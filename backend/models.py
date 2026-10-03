"""Response models for the Campus Customs API.

The product shape mirrors what the existing `chat_messages.products_json` rows
already contain, so the chatbot added in a later problem can return the same
objects the catalogue endpoints return.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SizeStock(BaseModel):
    """Stock for one product in one size."""

    size: str = Field(description="XS, S, M, L, XL or XXL.")
    quantity: int = Field(description="Units on hand. 0 means that size is out of stock.")
    in_stock: bool = Field(
        default=False, description="True when quantity is greater than zero."
    )

    def model_post_init(self, _context: object) -> None:
        # Derived rather than stored, so it can never disagree with quantity.
        object.__setattr__(self, "in_stock", self.quantity > 0)


class Product(BaseModel):
    """A catalogue row joined with its inventory.

    `colors` and `search_tags` are stored in SQLite as JSON text; they are
    parsed before they reach the client so the frontend never has to decode a
    string inside a string.
    """

    product_id: str = Field(description="URL-safe slug, also the image filename.")
    name: str
    garment_type: str
    description: str
    colors: list[str] = Field(default_factory=list)
    search_tags: list[str] = Field(default_factory=list)
    image_file_path: str = Field(description="Path as stored in the database.")
    image_url: str = Field(description="Public URL the browser can load.")
    price: float
    inventory: list[SizeStock] = Field(
        default_factory=list, description="All six sizes, in wearable order."
    )
    total_stock: int = Field(description="Sum of quantity across sizes.")


class ProductList(BaseModel):
    count: int
    products: list[Product]


class UserOut(BaseModel):
    """A user as returned by the API. Deliberately has no password field."""

    id: int
    name: str
    first_name: str | None = None
    last_name: str | None = None
    email: str
    created_at: str


class RegisterRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str
    confirm_password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    """Returned by both register and login."""

    user: UserOut
    token: str = Field(description="Signed session token; send as a Bearer header.")


# --------------------------------------------------------------------------
# Chat
# --------------------------------------------------------------------------


class ProductSummary(BaseModel):
    """A compact product view, returned by the agent's search tool.

    Smaller than `Product` on purpose: the agent needs enough to answer and
    cite, not every tag and the full description for a list of eight.
    """

    product_id: str
    name: str
    garment_type: str
    price: float
    colors: list[str] = Field(default_factory=list)
    sizes_in_stock: list[str] = Field(
        default_factory=list, description="Sizes with quantity greater than zero."
    )
    total_stock: int
    image_url: str


class StockReport(BaseModel):
    """Live stock for one product, from the inventory table."""

    product_id: str
    name: str
    sizes: list[SizeStock] = Field(default_factory=list)
    sizes_in_stock: list[str] = Field(default_factory=list)
    total_stock: int
    known_sizes: list[str] = Field(
        default_factory=list, description="Every size the shop stocks, in wearable order."
    )


class ProductCandidate(BaseModel):
    """One possible match when a shopper's wording is not specific."""

    product_id: str
    name: str
    garment_type: str
    price: float
    colors: list[str] = Field(default_factory=list)


class ProductLookup(BaseModel):
    """The result of trying to work out which product a shopper means.

    `ambiguous` is the important field: when it is true the agent must ask a
    clarifying question rather than picking a candidate itself.
    """

    found: bool
    match_type: Literal["product_id", "exact_name", "single_partial", "ambiguous", "none"]
    product_id: str | None = None
    candidates: list[ProductCandidate] = Field(default_factory=list)
    ambiguous: bool = False
    message: str = Field(
        description="Plain statement of what was or was not resolved, for the agent to act on."
    )


class ProductInfoResult(BaseModel):
    """Product facts, read from the catalogue table."""

    found: bool
    product_id: str | None = None
    name: str | None = None
    description: str | None = None
    garment_type: str | None = None
    price: float | None = Field(default=None, description="US dollars, from catalogue.price.")
    colors: list[str] = Field(default_factory=list)
    colors_listed: bool = Field(
        default=True,
        description="False when the product has no colours recorded — say so rather than guessing.",
    )
    image_url: str | None = None
    candidates: list[ProductCandidate] = Field(
        default_factory=list, description="Populated instead of a product when the wording was ambiguous."
    )
    message: str


class StockResult(BaseModel):
    """Live inventory for one product, optionally narrowed to one size."""

    found: bool
    product_id: str | None = None
    name: str | None = None
    requested_size: str | None = Field(
        default=None, description="Set when the shopper asked about one specific size."
    )
    quantity: int | None = Field(
        default=None, description="Units of the requested size. Only set when requested_size is."
    )
    in_stock: bool = Field(
        default=False,
        description="For a requested size, whether that size has stock; otherwise whether any size does.",
    )
    sizes: list[SizeStock] = Field(
        default_factory=list, description="Every size and its quantity, in wearable order."
    )
    sizes_in_stock: list[str] = Field(default_factory=list)
    total_stock: int = 0
    known_sizes: list[str] = Field(
        default_factory=list, description="The six sizes the shop stocks."
    )
    candidates: list[ProductCandidate] = Field(default_factory=list)
    message: str


class AgentReply(BaseModel):
    """What the agent itself returns.

    `product_ids` are slugs the agent actually looked up; the API turns them
    into full product objects so the chat widget can render real cards. The
    agent never invents a card — it can only cite ids a tool gave it.
    """

    reply: str = Field(description="The answer to show the shopper.")
    product_ids: list[str] = Field(
        default_factory=list,
        description="Catalogue ids of products referred to, for display as cards.",
    )


class ChatTurn(BaseModel):
    """One stored message from a signed-in shopper's history."""

    id: int
    role: Literal["user", "assistant"]
    content: str
    products: list[Product] = Field(default_factory=list)
    created_at: str


class ChatHistory(BaseModel):
    turns: list[ChatTurn] = Field(default_factory=list)
    persisted: bool = Field(
        description="True when signed in. Guests get an empty, unsaved history."
    )


class Shopper(BaseModel):
    """Who the agent is talking to.

    Carries only what the agent legitimately needs to be personable. There is
    no field for a password hash or a session token, so neither can reach the
    model.
    """

    user_id: int
    first_name: str | None = None
    last_name: str | None = None
    email: str

    @property
    def display_name(self) -> str:
        return (self.first_name or self.name_from_email).strip()

    @property
    def name_from_email(self) -> str:
        return self.email.split("@", 1)[0]


class ChatDeps(BaseModel):
    """Dependencies handed to the agent for one run.

    `shopper` is None for guests. `viewing` is the product the shopper has
    open, which is what lets "do you have this in pink?" resolve.
    """

    shopper: Shopper | None = None
    viewing: Product | None = None
    transcript: str = Field(
        default="", description="Earlier turns, replayed so references carry over."
    )
    served_product_ids: set[str] = Field(
        default_factory=set,
        description=(
            "Product ids the tools actually returned during this run. The "
            "route checks the agent's cited ids against this, so a card can "
            "only ever show a product a tool really found."
        ),
    )


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    product_id: str | None = Field(
        default=None,
        description="The product the shopper is looking at, if any, so 'this' resolves.",
    )


class ChatResponse(BaseModel):
    reply: str
    products: list[Product] = Field(
        default_factory=list, description="Full products matching the cited ids."
    )
    saved: bool = Field(
        default=False, description="True when the exchange was written to history."
    )
