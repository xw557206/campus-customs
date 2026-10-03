"""Read access to campus_customs.db.

Every product fact the site shows — price, colours, sizes, stock — comes from
here. Nothing is hardcoded in the frontend, so the database stays the single
source of truth.
"""

from __future__ import annotations

import json
import sqlite3
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from models import Product, SizeStock

# backend/db.py -> project root
ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "campus_customs.db"
PRODUCTS_DIR = ROOT / "products"

# The database stores sizes as plain text, which sorts alphabetically to
# L, M, S, XL, XS, XXL. Wearable order has to be imposed explicitly.
SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]
_SIZE_RANK = {s: i for i, s in enumerate(SIZE_ORDER)}

# Public URL prefix for product photos, matching the form already used in the
# saved chat history: /media/products/<slug>.jpg
MEDIA_PREFIX = "/media"


def connect() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No database at {DB_PATH}")
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def _parse_json_list(raw: Any) -> list[str]:
    """`colors` and `search_tags` are JSON arrays kept in TEXT columns.

    Decode them properly — splitting on commas corrupts the values.
    """
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return []
    return [str(v) for v in value] if isinstance(value, list) else []


def _to_product(row: sqlite3.Row, stock: list[sqlite3.Row]) -> Product:
    sizes = sorted(stock, key=lambda s: _SIZE_RANK.get(s["size"], len(SIZE_ORDER)))
    inventory = [SizeStock(size=s["size"], quantity=s["quantity"]) for s in sizes]
    image_file_path = row["image_file_path"]
    return Product(
        product_id=row["product_id"],
        name=row["name"],
        garment_type=row["garment_type"],
        description=row["description"],
        colors=_parse_json_list(row["colors"]),
        search_tags=_parse_json_list(row["search_tags"]),
        image_file_path=image_file_path,
        image_url=f"{MEDIA_PREFIX}/{image_file_path}",
        price=row["price"],
        inventory=inventory,
        total_stock=sum(i.quantity for i in inventory),
    )


def list_products(search: str | None = None) -> list[Product]:
    """Every product, optionally filtered by a free-text search.

    Search is deliberately case-insensitive and substring-based: `garment_type`
    is inconsistent in the data ("short-sleeve t-shirt" vs "short-sleeve
    T-shirt"), so an exact match would silently drop products.
    """
    con = connect()
    try:
        rows = con.execute("SELECT * FROM catalogue ORDER BY name").fetchall()
        stock: dict[str, list[sqlite3.Row]] = {}
        for s in con.execute("SELECT product_id, size, quantity FROM inventory"):
            stock.setdefault(s["product_id"], []).append(s)
    finally:
        con.close()

    products = [_to_product(r, stock.get(r["product_id"], [])) for r in rows]

    if search:
        needle = search.lower().strip()
        products = [
            p for p in products
            if needle in p.name.lower()
            or needle in p.garment_type.lower()
            or needle in p.description.lower()
            or any(needle in c.lower() for c in p.colors)
            or any(needle in t.lower() for t in p.search_tags)
        ]
    return products


def get_product_by_name(name: str) -> Product | None:
    """One product by its exact name, case-insensitively.

    Product names are unique across all 102 rows even when lower-cased, so an
    exact name is as reliable an identifier as the slug. Parameterised, like
    every query here.
    """
    con = connect()
    try:
        row = con.execute(
            "SELECT product_id FROM catalogue WHERE lower(name) = lower(?)",
            (name.strip(),),
        ).fetchone()
    finally:
        con.close()
    return get_product(row["product_id"]) if row else None


def find_by_name_fragment(fragment: str, limit: int = 10) -> list[Product]:
    """Products whose *name* contains the fragment, case-insensitively.

    Narrower than `list_products`, which also searches descriptions and tags.
    Used to decide whether a shopper's wording points at exactly one product
    or at several. Uses a bound parameter — the fragment is never interpolated
    into the SQL.
    """
    needle = fragment.strip()
    if not needle:
        return []
    con = connect()
    try:
        rows = con.execute(
            "SELECT product_id FROM catalogue WHERE lower(name) LIKE lower(?) ORDER BY name LIMIT ?",
            (f"%{needle}%", max(1, limit)),
        ).fetchall()
    finally:
        con.close()
    return [p for p in (get_product(r["product_id"]) for r in rows) if p]


def fuzzy_find(query: str, limit: int = 8, cutoff: float = 0.68) -> list[Product]:
    """Products whose name or tags are *close* to the query, for typos.

    Used only when an exact or substring search has already come back empty.
    Shoppers type "hoodi", "crewnek", "sweatshrt" — without this they get
    "we don't carry that", which is both wrong and unhelpful.

    Matching is done in Python over the catalogue (102 rows, already cached),
    not in SQL, because SQLite has no trigram or edit-distance support here.
    """
    needle = " ".join(query.lower().split())
    if len(needle) < 3:
        return []

    scored: list[tuple[float, int, Product]] = []
    for i, product in enumerate(list_products()):
        # Compare against the name, the garment type, and each tag; keep the
        # best similarity found for that product.
        haystacks = [product.name.lower(), product.garment_type.lower()]
        haystacks += [t.lower() for t in product.search_tags]
        haystacks += [c.lower() for c in product.colors]

        best = 0.0
        for candidate in haystacks:
            best = max(best, SequenceMatcher(None, needle, candidate).ratio())
            # Also compare word-by-word, so one misspelt word in a phrase
            # still matches a longer product name.
            for word in candidate.split():
                if len(word) > 2:
                    best = max(best, SequenceMatcher(None, needle, word).ratio() * 0.95)

        if best >= cutoff:
            scored.append((best, -i, product))

    scored.sort(key=lambda row: (row[0], row[1]), reverse=True)
    return [p for _, _, p in scored[: max(1, limit)]]


def get_product(product_id: str) -> Product | None:
    """One product by slug, or None if there is no such row."""
    con = connect()
    try:
        row = con.execute(
            "SELECT * FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchone()
        if row is None:
            return None
        stock = con.execute(
            "SELECT product_id, size, quantity FROM inventory WHERE product_id = ?",
            (product_id,),
        ).fetchall()
    finally:
        con.close()
    return _to_product(row, stock)
