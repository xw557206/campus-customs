"""Append-only audit trail for the Campus Customs agent.

Every agent run writes one record to `output/audit_trail.json`: when it ran,
which tools it called with what arguments, a short summary of what each tool
returned, and why the loop stopped. Earlier runs are never deleted or
rewritten — a run is appended to the end of the list and nothing else moves.

Why reconstruct the steps from the run's messages rather than logging from
inside each tool:

  * the tools stay clean — no audit plumbing threaded through business logic;
  * the record covers calls the tools never saw, such as a call the model
    made with malformed arguments and had to retry;
  * `finish_reason` and the usage counters come from the same place, so the
    stop reason is the model's own, not something inferred.

What is deliberately NOT recorded
---------------------------------
* No secrets. No API key, no password, no hash, no session token. The
  shopper is identified by numeric `user_id` only — never their email.
* No private reasoning. `ThinkingPart` content is skipped; only the fact
  that the model produced one is noted. An audit trail is a record of
  actions taken, not an attempt to capture hidden chain-of-thought.
* No unbounded blobs. Arguments and results are truncated so one chatty run
  cannot bloat the file.
"""

from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
AUDIT_PATH = HERE.parent / "output" / "audit_trail.json"

# Caps, so a single run cannot dominate the file.
MAX_ARG_CHARS = 200
MAX_RESULT_CHARS = 300
MAX_QUESTION_CHARS = 300
MAX_REPLY_CHARS = 300

# FastAPI runs sync endpoints in a thread pool, so two chats can finish at the
# same moment. The lock makes read-modify-write one atomic step.
_lock = threading.Lock()

logger = logging.getLogger("campus_customs.audit")


def now_iso() -> str:
    """UTC timestamp, seconds precision. Callers use it to mark a run's start."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _clip(value: Any, limit: int) -> str:
    """Render any value as a short single-line string."""
    if value is None:
        return ""
    if isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, default=str, ensure_ascii=False)
        except Exception:
            text = str(value)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _summarise_result(content: Any) -> str:
    """Describe what a tool returned without dumping the whole payload.

    Tool results are Pydantic models or lists of them. The useful audit facts
    are how many products came back and which ones — not every field of every
    row, which the catalogue already holds.
    """
    try:
        if isinstance(content, list):
            ids = [
                getattr(item, "product_id", None)
                or (item.get("product_id") if isinstance(item, dict) else None)
                for item in content
            ]
            ids = [i for i in ids if i]
            if ids:
                shown = ", ".join(ids[:5])
                extra = f" (+{len(ids) - 5} more)" if len(ids) > 5 else ""
                return f"{len(content)} result(s): {shown}{extra}"
            return f"{len(content)} result(s)"

        if hasattr(content, "model_dump"):
            data = content.model_dump()
        elif isinstance(content, dict):
            data = content
        else:
            return _clip(content, MAX_RESULT_CHARS)

        # Pull the few fields that actually say what happened.
        bits: list[str] = []
        for key in ("found", "ambiguous", "product_id", "name", "requested_size",
                    "quantity", "in_stock", "total_stock"):
            if key in data and data[key] is not None:
                bits.append(f"{key}={data[key]}")
        if data.get("candidates"):
            bits.append(f"candidates={len(data['candidates'])}")
        if data.get("message"):
            bits.append(f"message={data['message']}")
        return _clip("; ".join(bits) if bits else data, MAX_RESULT_CHARS)
    except Exception:
        return _clip(content, MAX_RESULT_CHARS)


def steps_from_messages(messages: list[Any]) -> tuple[list[dict[str, Any]], bool]:
    """Walk the run's messages and pull out one step per tool call.

    Returns the steps and whether the model emitted any thinking parts (noted
    as a count only — the content is never read or stored).
    """
    calls: dict[str, dict[str, Any]] = {}
    steps: list[dict[str, Any]] = []
    thinking = False
    iteration = 0

    for message in messages:
        for part in getattr(message, "parts", []):
            kind = getattr(part, "part_kind", "")

            if kind == "thinking":
                thinking = True
                continue

            if kind == "tool-call":
                tool_name = getattr(part, "tool_name", "unknown")
                # `final_result` is PydanticAI's internal output tool — the
                # model "calling" it is how a structured reply is delivered.
                # It is the stop step, not a catalogue lookup, so it is
                # labelled differently and does not count as an iteration.
                is_final = tool_name == "final_result"
                if not is_final:
                    iteration += 1
                try:
                    args = part.args_as_dict()
                except Exception:
                    args = getattr(part, "args", None)
                step = {
                    "iteration": None if is_final else iteration,
                    "action": "final_output" if is_final else "tool_call",
                    "tool_name": tool_name,
                    "tool_args": _clip(args, MAX_ARG_CHARS),
                    "result_summary": None,
                    "status": "pending",
                }
                steps.append(step)
                call_id = getattr(part, "tool_call_id", None)
                if call_id:
                    calls[call_id] = step

            elif kind == "tool-return":
                call_id = getattr(part, "tool_call_id", None)
                step = calls.get(call_id)
                if step is None:
                    continue
                step["result_summary"] = _summarise_result(getattr(part, "content", None))
                step["status"] = "ok"
                ts = getattr(part, "timestamp", None)
                if ts is not None:
                    step["at"] = ts.isoformat(timespec="seconds")

            elif kind == "retry-prompt":
                # The model called a tool in a way the schema rejected and was
                # asked to try again. Worth recording: it explains tool-call
                # counts that otherwise look inflated.
                call_id = getattr(part, "tool_call_id", None)
                step = calls.get(call_id)
                if step is not None:
                    step["status"] = "retry"
                    step["result_summary"] = _clip(
                        getattr(part, "content", "validation error"), MAX_RESULT_CHARS
                    )
                else:
                    steps.append({
                        "iteration": iteration,
                        "action": "retry",
                        "tool_name": getattr(part, "tool_name", None),
                        "tool_args": "",
                        "result_summary": _clip(
                            getattr(part, "content", "validation error"),
                            MAX_RESULT_CHARS,
                        ),
                        "status": "retry",
                    })

    return steps, thinking


def _load_existing() -> list[dict[str, Any]]:
    """Read the current trail. Never raises, never discards silently."""
    if not AUDIT_PATH.exists():
        return []
    try:
        raw = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    except Exception:
        # The file is unreadable. Preserve it rather than overwrite it — an
        # audit trail you can quietly destroy is not an audit trail.
        backup = AUDIT_PATH.with_suffix(f".corrupt-{int(datetime.now().timestamp())}.json")
        try:
            AUDIT_PATH.replace(backup)
            logger.error("Audit trail was unreadable; preserved it at %s", backup.name)
        except Exception:
            logger.exception("Audit trail unreadable and could not be preserved")
        return []
    return raw if isinstance(raw, list) else [raw]


def record_run(
    *,
    question: str,
    user_id: int | None,
    viewing_product_id: str | None,
    started_at: str,
    messages: list[Any] | None = None,
    usage: Any = None,
    finish_reason: str | None = None,
    stop_reason: str,
    status: str,
    reply: str | None = None,
    served_product_ids: list[str] | None = None,
    cited_product_ids: list[str] | None = None,
    dropped_product_ids: list[str] | None = None,
    error: str | None = None,
) -> str:
    """Append one run to the audit trail and return its run id.

    Never raises: a logging failure must not cost the shopper their answer.
    """
    run_id = f"run-{uuid.uuid4().hex[:12]}"
    try:
        steps, thinking = steps_from_messages(messages or [])

        record: dict[str, Any] = {
            "run_id": run_id,
            "started_at": started_at,
            "finished_at": now_iso(),
            "agent": "campus-customs",
            # Identify the shopper by id only — never email, never a token.
            "user_id": user_id,
            "viewing_product_id": viewing_product_id,
            "question": _clip(question, MAX_QUESTION_CHARS),
            # Catalogue tool calls only — the final_result step is excluded.
            "iterations": sum(1 for s in steps if s["action"] == "tool_call"),
            "steps": steps,
            "status": status,
            "stop_reason": stop_reason,
            "finish_reason": finish_reason,
            "model_thinking_emitted": thinking,
            "limits": {
                "request_limit": 12,
                "tool_calls_limit": 24,
                "search_result_cap": 12,
                "max_candidates": 8,
            },
        }

        if usage is not None:
            record["usage"] = {
                "requests": getattr(usage, "requests", None),
                "tool_calls": getattr(usage, "tool_calls", None),
                "input_tokens": getattr(usage, "input_tokens", None),
                "output_tokens": getattr(usage, "output_tokens", None),
            }
        if reply is not None:
            record["reply_summary"] = _clip(reply, MAX_REPLY_CHARS)
        if served_product_ids is not None:
            record["served_product_ids"] = sorted(served_product_ids)
        if cited_product_ids is not None:
            record["cited_product_ids"] = cited_product_ids
        if dropped_product_ids:
            record["dropped_product_ids"] = dropped_product_ids
        if error:
            record["error"] = _clip(error, MAX_RESULT_CHARS)

        with _lock:
            trail = _load_existing()
            trail.append(record)
            AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
            # Write to a sibling then replace, so an interrupted write cannot
            # truncate the existing trail.
            tmp = AUDIT_PATH.with_suffix(".json.tmp")
            tmp.write_text(
                json.dumps(trail, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            tmp.replace(AUDIT_PATH)
    except Exception:
        logger.exception("Could not append to the audit trail")

    return run_id
