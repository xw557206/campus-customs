"""Campus Customs API.

Serves the product catalogue and the product photos from campus_customs.db.

Run from the project root:
    .venv\\Scripts\\python.exe -m uvicorn backend.main:app --reload --port 8000

    API docs:  http://127.0.0.1:8000/docs
    Frontend:  http://127.0.0.1:5173
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Allow `python backend/main.py` as well as `uvicorn backend.main:app`.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from agent import AgentNotConfigured, is_configured, run_agent  # noqa: E402
from audit import now_iso as audit_now, record_run  # noqa: E402
from auth import create_token, read_token, secret_is_ephemeral  # noqa: E402
from db import PRODUCTS_DIR, get_product, list_products  # noqa: E402
from history import as_transcript, clear_history, load_history, save_turn  # noqa: E402
from models import (  # noqa: E402
    AuthResponse,
    ChatDeps,
    ChatHistory,
    ChatRequest,
    ChatResponse,
    LoginRequest,
    Product,
    ProductList,
    RegisterRequest,
    Shopper,
    UserOut,
)
from users import (  # noqa: E402
    AuthError,
    PublicUser,
    authenticate,
    create_user,
    get_user_by_id,
)

logger = logging.getLogger("campus_customs")

app = FastAPI(
    title="Campus Customs",
    version="0.1.0",
    description="Product catalogue for the Campus Customs storefront.",
)

# The Vite dev server runs on a different port in development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Product photos. The database stores "products/<slug>.jpg", so mounting the
# folder at /media makes the stored path resolve as /media/products/<slug>.jpg —
# the same form the saved chat history already uses.
if PRODUCTS_DIR.is_dir():
    app.mount("/media/products", StaticFiles(directory=PRODUCTS_DIR), name="media")


@app.get("/api/health")
def health() -> dict[str, object]:
    """Liveness check, with enough detail to spot a missing database early."""
    try:
        count = len(list_products())
        ok = True
    except Exception:
        count, ok = 0, False
    return {
        "ok": ok,
        "products": count,
        "images": PRODUCTS_DIR.is_dir(),
        # True means AUTH_SECRET is unset, so sessions end when the server
        # restarts. Fine in development; set AUTH_SECRET for anything else.
        "ephemeral_sessions": secret_is_ephemeral(),
        "assistant": is_configured(),
    }


@app.get("/api/products", response_model=ProductList)
def api_products(
    search: str | None = Query(default=None, description="Free-text filter."),
) -> ProductList:
    """The catalogue, each product joined with its per-size stock."""
    products = list_products(search)
    return ProductList(count=len(products), products=products)


@app.get("/api/products/{product_id}", response_model=Product)
def api_product(product_id: str) -> Product:
    """One product by slug."""
    product = get_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail=f"No product '{product_id}'")
    return product


# --------------------------------------------------------------------------
# Accounts
# --------------------------------------------------------------------------


def _as_user_out(user: PublicUser) -> UserOut:
    """Convert to the response model. There is no path here for the hash."""
    return UserOut(
        id=user.id,
        name=user.name,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        created_at=user.created_at,
    )


def current_user(authorization: str | None = Header(default=None)) -> UserOut:
    """Resolve the signed Bearer token to a user, or 401."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Not signed in.")
    user_id = read_token(authorization.split(" ", 1)[1].strip())
    if user_id is None:
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
    user = get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Not signed in.")
    return _as_user_out(user)


@app.post("/api/auth/register", response_model=AuthResponse, status_code=201)
def api_register(body: RegisterRequest) -> AuthResponse:
    """Create an account in the existing users table and sign the user in."""
    try:
        user = create_user(
            body.first_name, body.last_name, body.email,
            body.password, body.confirm_password,
        )
    except AuthError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message) from exc
    return AuthResponse(user=_as_user_out(user), token=create_token(user.id))


@app.post("/api/auth/login", response_model=AuthResponse)
def api_login(body: LoginRequest) -> AuthResponse:
    """Verify credentials against the stored hash."""
    try:
        user = authenticate(body.email, body.password)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message) from exc
    return AuthResponse(user=_as_user_out(user), token=create_token(user.id))


@app.get("/api/auth/me", response_model=UserOut)
def api_me(user: UserOut = Depends(current_user)) -> UserOut:
    """Who the current token belongs to."""
    return user


def optional_user(authorization: str | None = Header(default=None)) -> UserOut | None:
    """Resolve a Bearer token if one is present, else None.

    Unlike `current_user`, a missing or invalid token is not an error — guests
    are allowed to chat, they just get no saved history.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    user_id = read_token(authorization.split(" ", 1)[1].strip())
    if user_id is None:
        return None
    user = get_user_by_id(user_id)
    return _as_user_out(user) if user else None


@app.get("/api/chat/history", response_model=ChatHistory)
def api_chat_history(user: UserOut | None = Depends(optional_user)) -> ChatHistory:
    """Past conversation for a signed-in shopper; empty for a guest."""
    if user is None:
        return ChatHistory(turns=[], persisted=False)
    return ChatHistory(turns=load_history(user.id), persisted=True)


@app.delete("/api/chat/history", status_code=204)
def api_clear_history(user: UserOut = Depends(current_user)) -> None:
    """Let a signed-in shopper delete their own history."""
    clear_history(user.id)


@app.post("/api/chat", response_model=ChatResponse)
def api_chat(
    body: ChatRequest, user: UserOut | None = Depends(optional_user)
) -> ChatResponse:
    """Ask the Campus Customs agent a question.

    The agent answers in prose and cites catalogue ids; those ids are expanded
    here into full product objects so the widget can render real cards. Only
    ids that exist in the catalogue survive, so a hallucinated id becomes
    nothing rather than a broken card.
    """
    # Build the agent's context: who is chatting, what they have open, and
    # what was said earlier. All three are optional.
    shopper = (
        Shopper(
            user_id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
        )
        if user
        else None
    )
    past = load_history(user.id) if user else []
    deps = ChatDeps(
        shopper=shopper,
        viewing=get_product(body.product_id) if body.product_id else None,
        transcript=as_transcript(past),
    )

    # Every run is audited, including the ones that fail. `audit_common` is
    # the context that is true whichever way the run ends.
    started_at = audit_now()
    audit_common = {
        "question": body.message,
        "user_id": user.id if user else None,
        "viewing_product_id": body.product_id,
        "started_at": started_at,
    }

    try:
        run = run_agent(body.message, deps)
        answer = run.output
    except AgentNotConfigured as exc:
        # A setup problem, not a user error. Safe to name, no secrets in it.
        logger.warning("Chat unavailable: %s", exc)
        record_run(
            **audit_common,
            stop_reason="agent_not_configured",
            status="unavailable",
            error=str(exc),
        )
        raise HTTPException(
            status_code=503,
            detail="The shop assistant isn't available right now.",
        ) from exc
    except Exception as exc:
        # The provider's own safety filter can reject a message before the
        # agent sees it. That is a refusal, not a fault — answer it the way
        # the assistant would rather than showing an error.
        if "content_filter" in str(exc) or "content management policy" in str(exc):
            logger.info("Provider content filter declined a message")
            record_run(
                **audit_common,
                stop_reason="provider_content_filter",
                status="refused",
            )
            return ChatResponse(
                reply=(
                    "I'm not able to help with that one. I'm here for Campus "
                    "Customs — ask me about a product, a price, or what sizes "
                    "we have in stock."
                ),
                products=[],
            )
        # A run that blows the request or tool-call ceiling lands here too.
        limit_hit = "limit" in type(exc).__name__.lower() or "exceeded" in str(exc).lower()
        record_run(
            **audit_common,
            stop_reason="usage_limit_exceeded" if limit_hit else "error",
            status="error",
            error=f"{type(exc).__name__}: {exc}",
        )
        # Never let a provider error, traceback, or key reach the browser.
        logger.exception("Chat request failed")
        raise HTTPException(
            status_code=502,
            detail="Sorry — the assistant couldn't answer that just now. Please try again.",
        ) from None

    # Hallucination guard. A card is rendered only for an id that (a) a tool
    # actually returned during this run, and (b) exists in the catalogue.
    # An id the model invented satisfies neither and is dropped.
    cited = list(dict.fromkeys(answer.product_ids))
    unserved = [pid for pid in cited if pid not in deps.served_product_ids]
    if unserved:
        logger.warning(
            "Agent cited %d product id(s) no tool returned: %s", len(unserved), unserved
        )
    products = [
        p
        for p in (
            get_product(pid) for pid in cited if pid in deps.served_product_ids
        )
        if p
    ]

    # The successful-run record. `dropped_product_ids` is the interesting
    # column: a non-empty value means the guard caught the model citing a
    # product no tool had returned.
    record_run(
        **audit_common,
        messages=run.messages,
        usage=run.usage,
        finish_reason=run.finish_reason,
        stop_reason="completed",
        status="ok",
        reply=answer.reply,
        served_product_ids=list(deps.served_product_ids),
        cited_product_ids=cited,
        dropped_product_ids=unserved,
    )

    # Persist for signed-in shoppers only. Guests chat freely, nothing stored.
    saved = False
    if user is not None:
        try:
            save_turn(user.id, "user", body.message)
            save_turn(user.id, "assistant", answer.reply, products)
            saved = True
        except Exception:
            # A history write must never cost the shopper their answer.
            logger.exception("Could not save chat history for user %s", user.id)

    return ChatResponse(reply=answer.reply, products=products, saved=saved)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
