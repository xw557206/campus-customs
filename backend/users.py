"""Reads and writes against the existing `users` table.

The table shipped with the database and is used as-is — no second user store,
no schema replacement. `name` is NOT NULL and predates `first_name` /
`last_name` (which were added later by ALTER TABLE), so all three are written
on sign-up to keep them consistent.

`password_hash` never leaves this module in any value returned to a caller.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass

from auth import hash_password, verify_password
from db import connect

# Deliberately permissive: enough to catch a typo, not an attempt to decide
# which addresses are "real".
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

MIN_PASSWORD_LENGTH = 8


class AuthError(Exception):
    """A sign-up or sign-in problem that is safe to show the user."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


@dataclass(frozen=True)
class PublicUser:
    """A user as the API is allowed to expose them — no hash, ever."""

    id: int
    name: str
    first_name: str | None
    last_name: str | None
    email: str
    created_at: str


def _to_public(row: sqlite3.Row) -> PublicUser:
    return PublicUser(
        id=row["id"],
        name=row["name"],
        first_name=row["first_name"],
        last_name=row["last_name"],
        email=row["email"],
        created_at=row["created_at"],
    )


def normalise_email(email: str) -> str:
    return email.strip().lower()


def get_user_by_id(user_id: int) -> PublicUser | None:
    con = connect()
    try:
        row = con.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    finally:
        con.close()
    return _to_public(row) if row else None


def create_user(
    first_name: str, last_name: str, email: str, password: str, confirm: str
) -> PublicUser:
    """Validate and insert a new account. Raises AuthError on any problem."""
    first_name = first_name.strip()
    last_name = last_name.strip()
    email = normalise_email(email)

    if not first_name:
        raise AuthError("Please enter your first name.")
    if not last_name:
        raise AuthError("Please enter your last name.")
    if not email:
        raise AuthError("Please enter your email address.")
    if not EMAIL_RE.match(email):
        raise AuthError("That doesn't look like a valid email address.")
    if not password:
        raise AuthError("Please choose a password.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AuthError(
            f"Please use at least {MIN_PASSWORD_LENGTH} characters in your password."
        )
    if password != confirm:
        raise AuthError("Those passwords don't match.")

    con = connect()
    try:
        existing = con.execute(
            "SELECT id FROM users WHERE lower(email) = ?", (email,)
        ).fetchone()
        if existing:
            raise AuthError("An account with that email already exists.", status=409)

        # `name` is NOT NULL and older than first_name/last_name; write all
        # three so the row stays internally consistent.
        full_name = f"{first_name} {last_name}"
        cursor = con.execute(
            """
            INSERT INTO users (name, email, password_hash, first_name, last_name)
            VALUES (?, ?, ?, ?, ?)
            """,
            (full_name, email, hash_password(password), first_name, last_name),
        )
        con.commit()
        row = con.execute(
            "SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
    except sqlite3.IntegrityError as exc:
        # The UNIQUE constraint on email is the backstop if two sign-ups race.
        raise AuthError("An account with that email already exists.", status=409) from exc
    finally:
        con.close()

    return _to_public(row)


def authenticate(email: str, password: str) -> PublicUser:
    """Verify credentials. Raises AuthError with a deliberately vague message."""
    email = normalise_email(email)
    if not email or not password:
        raise AuthError("Please enter your email and password.")

    con = connect()
    try:
        row = con.execute(
            "SELECT * FROM users WHERE lower(email) = ?", (email,)
        ).fetchone()
    finally:
        con.close()

    # One message for "no such email" and for "wrong password", so the response
    # cannot be used to discover which addresses have accounts.
    generic = AuthError("Email or password is incorrect.", status=401)

    if row is None:
        # Still spend the work a real verification would, so the timing of a
        # miss doesn't stand out from a wrong password.
        verify_password(password, "$2b$12$" + "." * 53)
        raise generic

    if not verify_password(password, row["password_hash"]):
        raise generic

    return _to_public(row)
