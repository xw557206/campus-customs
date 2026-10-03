"""Chat history for signed-in shoppers.

Reads and writes the `chat_messages` table that shipped with the database —
no new table, no second store. The table already has a foreign key to
`users(id)`, so history is tied to a stable user id rather than an email that
could change.

Guests are never written here. A guest conversation lives only in their
browser tab and disappears when they leave, which is what the brief asks for.

Nothing sensitive is stored: only the role, the message text, and the ids of
products an answer referred to. No tokens, no password material, no headers.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from db import connect, get_product
from models import ChatTurn, Product

# How much of the past conversation to reload and to replay to the agent.
# Enough for "do you have this in pink?" to resolve against earlier turns,
# small enough that the context stays affordable.
HISTORY_LIMIT = 20


def load_history(user_id: int, limit: int = HISTORY_LIMIT) -> list[ChatTurn]:
    """The most recent turns for one user, oldest first.

    Ordered by `id`, which is the autoincrement primary key — reliable even
    when two messages share a `created_at` second, which turn pairs routinely
    do.
    """
    con = connect()
    try:
        rows = con.execute(
            """
            SELECT id, role, content, products_json, created_at
            FROM chat_messages
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, max(1, limit)),
        ).fetchall()
    finally:
        con.close()

    turns: list[ChatTurn] = []
    for row in reversed(rows):  # back into chronological order
        turns.append(
            ChatTurn(
                id=row["id"],
                role=row["role"],
                content=row["content"],
                products=_products_from_json(row["products_json"]),
                created_at=row["created_at"],
            )
        )
    return turns


def _products_from_json(raw: Any) -> list[Product]:
    """Rebuild product cards from a stored row.

    Only the ids are trusted: each is re-read from the catalogue, so a card
    always shows today's price and stock rather than whatever was true when
    the message was first sent.
    """
    if not raw:
        return []
    try:
        stored = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(stored, list):
        return []

    products: list[Product] = []
    for item in stored:
        pid = item.get("product_id") if isinstance(item, dict) else item
        if not isinstance(pid, str):
            continue
        product = get_product(pid)
        if product:
            products.append(product)
    return products


def save_turn(
    user_id: int,
    role: Literal["user", "assistant"],
    content: str,
    products: list[Product] | None = None,
) -> int:
    """Append one message. Returns its new id.

    `products_json` stores ids only — the row stays small and can never go
    stale, since the products are re-read on load.
    """
    payload = (
        json.dumps([{"product_id": p.product_id} for p in products])
        if products
        else None
    )
    con = connect()
    try:
        cursor = con.execute(
            """
            INSERT INTO chat_messages (user_id, role, content, products_json)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, role, content, payload),
        )
        con.commit()
        return int(cursor.lastrowid or 0)
    finally:
        con.close()


def clear_history(user_id: int) -> int:
    """Delete one user's history. Returns how many rows went."""
    con = connect()
    try:
        cursor = con.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,))
        con.commit()
        return cursor.rowcount
    finally:
        con.close()


def as_transcript(turns: list[ChatTurn]) -> str:
    """Render past turns as plain text for the agent's context.

    Replayed as a readable transcript rather than as PydanticAI message
    objects, because the stored rows are text — they were not produced by this
    agent's own message format and some predate it entirely.
    """
    if not turns:
        return ""
    lines = []
    for turn in turns:
        who = "Shopper" if turn.role == "user" else "You"
        lines.append(f"{who}: {turn.content}")
    return "\n".join(lines)
