"""The Campus Customs PydanticAI agent.

Holds everything about how the agent is configured: the model, the provider,
the system prompt, and the tools it may call. `main.py` only calls
`answer_question()` and does not know how any of this is wired.

Configuration comes from the environment, never from source:

    PORTKEY_API_KEY   required — the gateway key, read from the root .env
    MODEL_NAME        optional — defaults to the course model
    PORTKEY_BASE_URL  optional — defaults to the Portkey gateway
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic_ai import Agent, UsageLimits
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from pydantic_ai import RunContext

from models import AgentReply, ChatDeps
from tools import AGENT_TOOLS

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROMPT_PATH = HERE / "prompts" / "prompt.md"

# .env may sit beside the backend or at the project root.
load_dotenv(ROOT / ".env")
load_dotenv(ROOT.parent / ".env")

MODEL_NAME = os.getenv("MODEL_NAME", "gpt-5.6-luna")
PORTKEY_BASE_URL = os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1")

# Bounds a confused loop without cutting off legitimate work. A broad question
# ("what hoodies do you have?") can reasonably be one search plus a lookup per
# result, so the tool ceiling has to clear that comfortably — an earlier limit
# of 8 rejected a real 15-call answer.
RUN_LIMITS = UsageLimits(request_limit=12, tool_calls_limit=24)


class AgentNotConfigured(RuntimeError):
    """Raised when the API key is missing, so the route can answer cleanly."""


_agent: Agent | None = None


def load_prompt() -> str:
    """Read the system prompt from prompts/prompt.md.

    Kept in markdown rather than in Python so the shop's voice and rules can
    be edited without touching code.
    """
    if not PROMPT_PATH.exists():
        raise AgentNotConfigured(f"System prompt missing at {PROMPT_PATH}")
    return PROMPT_PATH.read_text(encoding="utf-8")


def get_agent() -> Agent:
    """Build the agent once, lazily.

    Lazy so the rest of the API — products, auth — still imports and runs with
    no API key present. Only a chat request needs one.
    """
    global _agent
    if _agent is None:
        api_key = os.getenv("PORTKEY_API_KEY")
        if not api_key:
            raise AgentNotConfigured(
                "PORTKEY_API_KEY is not set. Add it to the project .env "
                "so the assistant can start."
            )
        model = OpenAIChatModel(
            MODEL_NAME,
            provider=OpenAIProvider(base_url=PORTKEY_BASE_URL, api_key=api_key),
        )
        _agent = Agent(
            model,
            name="campus-customs",
            instructions=load_prompt(),
            output_type=AgentReply,
            deps_type=ChatDeps,
            tools=AGENT_TOOLS,
        )
        _register_context(_agent)
    return _agent


def _register_context(agent: Agent) -> None:
    """Attach the per-run context as dynamic instructions.

    PydanticAI's `@agent.instructions` runs on every request, so who is
    chatting, what they are looking at, and what was said earlier are built
    fresh each time rather than baked into the static prompt.
    """

    @agent.instructions
    def who_is_chatting(ctx: RunContext[ChatDeps]) -> str:
        shopper = ctx.deps.shopper if ctx.deps else None
        if shopper is None:
            return (
                "## Who you are talking to\n\n"
                "A guest — nobody signed in. Do not greet them by name and do "
                "not refer to past conversations; you have no history with "
                "them. You may mention that creating an account keeps their "
                "chat history, but only if it comes up naturally."
            )
        full = " ".join(p for p in (shopper.first_name, shopper.last_name) if p)
        return (
            "## Who you are talking to\n\n"
            f"{full or shopper.display_name}, a signed-in customer "
            f"(account id {shopper.user_id}, {shopper.email}). You may greet "
            f"them by their first name. Use this only to be personable — "
            "never read their details back to them unprompted, and never "
            "repeat their email in an answer unless they ask for it."
        )

    @agent.instructions
    def what_they_are_looking_at(ctx: RunContext[ChatDeps]) -> str:
        product = ctx.deps.viewing if ctx.deps else None
        if product is None:
            return (
                "## What they are looking at\n\n"
                "They are not on a product page. If they say \"this\" or "
                "\"it\" without naming a product, ask which one they mean."
            )
        in_stock = [s.size for s in product.inventory if s.quantity > 0]
        return (
            "## What they are looking at\n\n"
            f"The shopper currently has **{product.name}** open "
            f"(id `{product.product_id}`). When they say \"this\", \"it\", or "
            "\"this one\", they mean that product.\n\n"
            f"For reference — price ${product.price:.0f}; colours "
            f"{', '.join(product.colors) if product.colors else 'not listed'}; "
            f"sizes in stock {', '.join(in_stock) if in_stock else 'none'}.\n\n"
            "Still call the tools before quoting any of this back: the page "
            "context can be stale, the tools cannot."
        )

    @agent.instructions
    def earlier_in_the_conversation(ctx: RunContext[ChatDeps]) -> str:
        transcript = ctx.deps.transcript if ctx.deps else ""
        if not transcript:
            return ""
        return (
            "## Earlier in this conversation\n\n"
            "Use it to understand what they are referring to. Do not reuse "
            "any price or stock figure from it — re-check those with the "
            "tools, because they change.\n\n"
            f"{transcript}"
        )


@dataclass
class AgentRun:
    """One completed agent run, with the detail the audit trail needs.

    `answer_question` returns only the reply, which is all most callers want.
    The chat route needs the messages and counters as well, so it can record
    which tools ran and why the loop stopped.
    """

    output: AgentReply
    messages: list[Any]
    usage: Any
    finish_reason: str | None


def run_agent(message: str, deps: ChatDeps | None = None) -> AgentRun:
    """Run one shopper question through the agent, keeping the run detail."""
    result = get_agent().run_sync(
        message, deps=deps or ChatDeps(), usage_limits=RUN_LIMITS
    )
    messages = result.all_messages()
    # The stop reason reported by the model on its final response.
    finish_reason = None
    for msg in reversed(messages):
        reason = getattr(msg, "finish_reason", None)
        if reason is not None:
            finish_reason = str(reason)
            break
    return AgentRun(
        output=result.output,
        messages=messages,
        # `usage` is a property on AgentRunResult in pydantic-ai 2.x, not a call.
        usage=result.usage,
        finish_reason=finish_reason,
    )


def answer_question(message: str, deps: ChatDeps | None = None) -> AgentReply:
    """Run one shopper question through the agent and return just the reply."""
    return run_agent(message, deps).output


def is_configured() -> bool:
    """Whether a chat request could succeed, without building the agent."""
    return bool(os.getenv("PORTKEY_API_KEY")) and PROMPT_PATH.exists()
