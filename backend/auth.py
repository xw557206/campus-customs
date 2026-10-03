"""Password hashing, verification, and session tokens.

Two hash schemes are supported on purpose:

* **bcrypt** — used for every account created from now on. The library
  generates its own random salt and verification goes through `bcrypt.checkpw`,
  never a hand-rolled string comparison.
* **pbkdf2_sha256** — the scheme the three seeded accounts already use, stored
  as `pbkdf2_sha256$<salt>$<hex digest>` with 120,000 iterations of SHA-256.
  Verifying it is read-only; nothing new is ever written in this format.

Supporting the legacy scheme is what lets the seeded `test@campuscustoms.yale.edu`
account keep working without rewriting rows in the supplied database.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time

import bcrypt

# --------------------------------------------------------------------------
# Password hashing
# --------------------------------------------------------------------------

LEGACY_PREFIX = "pbkdf2_sha256$"
LEGACY_ITERATIONS = 120_000
LEGACY_ALGORITHM = "sha256"


def hash_password(password: str) -> str:
    """Hash a new password with bcrypt, which salts it for us."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def _verify_legacy(password: str, stored: str) -> bool:
    """Check a password against the seeded pbkdf2_sha256$salt$hex format."""
    try:
        _, salt, expected = stored.split("$", 2)
    except ValueError:
        return False
    derived = hashlib.pbkdf2_hmac(
        LEGACY_ALGORITHM, password.encode("utf-8"), salt.encode("utf-8"),
        LEGACY_ITERATIONS,
    ).hex()
    # Constant-time: a timing difference here leaks the digest byte by byte.
    return hmac.compare_digest(derived, expected)


def verify_password(password: str, stored: str) -> bool:
    """Verify a password against whichever scheme the stored hash uses."""
    if not stored:
        return False
    if stored.startswith(LEGACY_PREFIX):
        return _verify_legacy(password, stored)
    try:
        return bcrypt.checkpw(password.encode("utf-8"), stored.encode("utf-8"))
    except (ValueError, TypeError):
        # Malformed hash in the row — treat as a failed login, never a crash.
        return False


def needs_rehash(stored: str) -> bool:
    """True when a hash is in the legacy format and could be upgraded."""
    return stored.startswith(LEGACY_PREFIX)


# --------------------------------------------------------------------------
# Session tokens
# --------------------------------------------------------------------------
#
# A small signed token rather than a full session system: the payload is
# readable but cannot be altered without the secret, so the backend can trust
# the user id on a later request. There is no refresh or revocation — enough
# for this storefront, not a replacement for a real session layer.

TOKEN_TTL_SECONDS = 7 * 24 * 60 * 60  # one week

_SECRET = os.getenv("AUTH_SECRET") or secrets.token_hex(32)
_SECRET_FROM_ENV = bool(os.getenv("AUTH_SECRET"))


def secret_is_ephemeral() -> bool:
    """True when AUTH_SECRET was not set, so tokens die with the process."""
    return not _SECRET_FROM_ENV


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def create_token(user_id: int) -> str:
    payload = {"sub": user_id, "exp": int(time.time()) + TOKEN_TTL_SECONDS}
    body = _b64(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(_SECRET.encode(), body.encode(), hashlib.sha256).digest()
    return f"{body}.{_b64(signature)}"


def read_token(token: str) -> int | None:
    """Return the user id in a valid, unexpired token, else None."""
    try:
        body, signature = token.split(".", 1)
    except ValueError:
        return None
    expected = hmac.new(_SECRET.encode(), body.encode(), hashlib.sha256).digest()
    if not hmac.compare_digest(_unb64(signature), expected):
        return None
    try:
        payload = json.loads(_unb64(body))
    except (ValueError, json.JSONDecodeError):
        return None
    if payload.get("exp", 0) < time.time():
        return None
    sub = payload.get("sub")
    return int(sub) if isinstance(sub, int) else None
