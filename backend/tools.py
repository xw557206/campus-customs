"""Tools the Campus Customs agent can call.

Everything reads through `db.py`, the same layer the product pages use, so the
chatbot and the website can never disagree about price or stock. All SQL in
that layer is parameterised — no shopper input is ever interpolated into a
query.

Only fields that exist in `campus_customs.db` are exposed:

    catalogue  product_id, name, garment_type, description, colors,
               search_tags, image_file_path, price
    inventory  product_id, size, quantity   (unique per product+size)

There is no SKU column and no colour-level stock. Inventory is tracked per
product *and size only*, so "is the navy one in medium?" can only be answered
at product-and-size level.
"""

from __future__ import annotations

from pydantic_ai import RunContext

from db import (
    SIZE_ORDER,
    find_by_name_fragment,
    fuzzy_find,
    get_product,
    get_product_by_name,
    list_products,
)
from models import (
    ChatDeps,
    Product,
    ProductCandidate,
    ProductInfoResult,
    ProductLookup,
    ProductSummary,
    StockResult,
)

MAX_CANDIDATES = 8


def _record(ctx: RunContext[ChatDeps] | None, *product_ids: str) -> None:
    """Note which products a tool actually returned.

    `main.py` only renders cards for ids in this set, so an id the model
    invents has nowhere to come from.
    """
    if ctx is not None and ctx.deps is not None:
        ctx.deps.served_product_ids.update(pid for pid in product_ids if pid)


def _candidate(p: Product) -> ProductCandidate:
    return ProductCandidate(
        product_id=p.product_id,
        name=p.name,
        garment_type=p.garment_type,
        price=p.price,
        colors=p.colors,
    )


def _summarise(p: Product) -> ProductSummary:
    return ProductSummary(
        product_id=p.product_id,
        name=p.name,
        garment_type=p.garment_type,
        price=p.price,
        colors=p.colors,
        sizes_in_stock=[s.size for s in p.inventory if s.quantity > 0],
        total_stock=p.total_stock,
        image_url=p.image_url,
    )


def _resolve(identifier: str) -> tuple[Product | None, ProductLookup]:
    """Work out which product a string refers to.

    Strongest identifier first, because guessing is the failure mode worth
    avoiding:

    1. `product_id` — the catalogue slug, exact.
    2. exact product name, case-insensitive. Names are unique across all 102
       rows, so this is as safe as the slug.
    3. a name fragment that matches exactly one product.

    If a fragment matches several, nothing is chosen: the candidates come back
    with `ambiguous=True` so the agent asks which one is meant.
    """
    text = (identifier or "").strip()
    if not text:
        return None, ProductLookup(
            found=False, match_type="none", ambiguous=False,
            message="No product was named.",
        )

    exact = get_product(text)
    if exact:
        return exact, ProductLookup(
            found=True, match_type="product_id", product_id=exact.product_id,
            message=f"Matched catalogue id {exact.product_id}.",
        )

    by_name = get_product_by_name(text)
    if by_name:
        return by_name, ProductLookup(
            found=True, match_type="exact_name", product_id=by_name.product_id,
            message=f"Matched the product named {by_name.name}.",
        )

    partial = find_by_name_fragment(text, limit=MAX_CANDIDATES + 1)
    if len(partial) == 1:
        only = partial[0]
        return only, ProductLookup(
            found=True, match_type="single_partial", product_id=only.product_id,
            message=f"Only one product name contains that wording: {only.name}.",
        )
    if len(partial) > 1:
        return None, ProductLookup(
            found=False, match_type="ambiguous", ambiguous=True,
            candidates=[_candidate(p) for p in partial[:MAX_CANDIDATES]],
            message=(
                f"{len(partial)} products match that wording. Ask the shopper "
                "which one they mean — do not choose for them."
            ),
        )

    return None, ProductLookup(
        found=False, match_type="none", ambiguous=False,
        message=(
            f"No product matches '{text}'. Say we do not seem to carry it; "
            "do not offer a different product as if it were the one asked for."
        ),
    )


# --------------------------------------------------------------------------
# Tools
# --------------------------------------------------------------------------


def search_catalogue(
    ctx: RunContext[ChatDeps], query: str, limit: int = 8
) -> list[ProductSummary]:
    """Search the catalogue by free text, for browsing-style questions.

    Matches against product name, garment type, description, colours and
    search tags. Use this when a shopper describes what they want rather than
    naming a product — "navy hoodie", "something for The Game".

    For a question about one specific product, prefer `get_product_info` or
    `check_stock`, which identify a product precisely.

    Args:
        query: What the shopper described.
        limit: Maximum products to return, capped at 12.

    Returns:
        Matching products with price, colours, and the sizes in stock. Empty
        when nothing matches — say we do not carry it rather than substituting.
    """
    capped = max(1, min(limit, 12))
    matches = list_products(query)[:capped]

    # Shoppers mistype. If nothing matched exactly, try a close match before
    # telling them we do not carry it.
    if not matches:
        matches = fuzzy_find(query, limit=capped)

    _record(ctx, *(p.product_id for p in matches))
    return [_summarise(p) for p in matches]


def get_product_info(ctx: RunContext[ChatDeps], identifier: str) -> ProductInfoResult:
    """Name, description and price for one product.

    Use this for any question about what a product is, what it looks like, or
    what it costs.

    Args:
        identifier: A catalogue id (slug) such as "basic-hoodie-big-yale", or
            the product's exact name. A partial name works only when it points
            at a single product.

    Returns:
        `found=True` with name, description, price and colours; or
        `found=False`. When the wording is ambiguous, `candidates` lists the
        possibilities and the message says to ask which one — do not pick one.
    """
    product, lookup = _resolve(identifier)
    if product is None:
        # Candidates are offered for clarification, so they count as served.
        _record(ctx, *(c.product_id for c in lookup.candidates))
        return ProductInfoResult(
            found=False, candidates=lookup.candidates, message=lookup.message
        )

    _record(ctx, product.product_id)

    return ProductInfoResult(
        found=True,
        product_id=product.product_id,
        name=product.name,
        description=product.description,
        garment_type=product.garment_type,
        price=product.price,
        colors=product.colors,
        # Three products have no colours recorded. Flag it so the agent says
        # "not listed" instead of inferring a colour from the description.
        colors_listed=bool(product.colors),
        image_url=product.image_url,
        message=f"{product.name} costs ${product.price:.0f}.",
    )


def check_stock(
    ctx: RunContext[ChatDeps], identifier: str, size: str | None = None
) -> StockResult:
    """Live stock for a product, optionally for one size.

    Use this before telling a shopper anything is available, and whenever they
    ask about a size. Quantities are read at the moment of the call.

    Args:
        identifier: A catalogue id (slug) or the product's exact name.
        size: Optionally one of XS, S, M, L, XL, XXL. Omit to get every size.

    Returns:
        When a size is given: `quantity` and `in_stock` for that size. A
        `quantity` of 0 means that size is out of stock — say so, and do not
        imply another size is available unless it appears in `sizes_in_stock`.
        When no size is given: every size with its quantity.
        `found=False` means the product or size could not be identified.
    """
    product, lookup = _resolve(identifier)
    if product is None:
        _record(ctx, *(c.product_id for c in lookup.candidates))
        return StockResult(
            found=False, candidates=lookup.candidates,
            known_sizes=list(SIZE_ORDER), message=lookup.message,
        )

    _record(ctx, product.product_id)

    sizes = product.inventory
    in_stock_sizes = [s.size for s in sizes if s.quantity > 0]

    if size:
        wanted = size.strip().upper()
        match = next((s for s in sizes if s.size == wanted), None)
        if match is None:
            return StockResult(
                found=False,
                product_id=product.product_id,
                name=product.name,
                requested_size=wanted,
                sizes=sizes,
                sizes_in_stock=in_stock_sizes,
                total_stock=product.total_stock,
                known_sizes=list(SIZE_ORDER),
                message=(
                    f"'{wanted}' is not a size we stock. We carry "
                    f"{', '.join(SIZE_ORDER)}."
                ),
            )

        available = match.quantity > 0
        return StockResult(
            found=True,
            product_id=product.product_id,
            name=product.name,
            requested_size=wanted,
            quantity=match.quantity,
            in_stock=available,
            sizes=sizes,
            sizes_in_stock=in_stock_sizes,
            total_stock=product.total_stock,
            known_sizes=list(SIZE_ORDER),
            message=(
                f"{product.name} in {wanted}: {match.quantity} in stock."
                if available
                else f"{product.name} in {wanted} is out of stock."
            ),
        )

    return StockResult(
        found=True,
        product_id=product.product_id,
        name=product.name,
        in_stock=bool(in_stock_sizes),
        sizes=sizes,
        sizes_in_stock=in_stock_sizes,
        total_stock=product.total_stock,
        known_sizes=list(SIZE_ORDER),
        message=(
            f"{product.name} is available in {', '.join(in_stock_sizes)}."
            if in_stock_sizes
            else f"{product.name} is out of stock in every size."
        ),
    )


def get_product_details(ctx: RunContext[ChatDeps], product_id: str) -> Product | None:
    """The complete catalogue row for one product, by exact id.

    Use this only when you need every field at once — full description, all
    colours, all search tags, and the quantity in each size. For a price or a
    description, `get_product_info` is lighter.

    Args:
        product_id: The catalogue slug, e.g. "basic-hoodie-big-yale".

    Returns:
        The product, or None when no product has that id.
    """
    product = get_product(product_id)
    if product:
        _record(ctx, product.product_id)
    return product


# Registered on the agent in agent.py.
AGENT_TOOLS = [search_catalogue, get_product_info, check_stock, get_product_details]
