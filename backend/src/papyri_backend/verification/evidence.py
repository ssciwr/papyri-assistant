"""Render what the agent retrieved, so a reviewer can check the answer against it.

The reviewer needs each tool result next to the call that produced it: check 5
of its prompt compares the call's arguments with the claim the result is used
for. A ``ToolMessage`` carries only the result, so it is joined here to the
tool call on the ``AIMessage`` that requested it. Each result is cut to a
maximum length, so one very large result cannot crowd the others out of the
reviewer's single model call.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

_UNKNOWN_TOOL = "unknown"  # summarization can drop the call while keeping its result


def evidence_blocks(messages: Sequence[Any], *, max_chars: int) -> list[str]:
    """Render each tool result in ``messages`` with the call that produced it.

    Args:
        messages: The messages to take evidence from, oldest first.
        max_chars: Longest result text kept per block.

    Returns:
        One text block per tool result, in call order, headed by the tool name
        and its arguments.
    """
    calls: dict[str, dict[str, Any]] = {}
    blocks: list[str] = []

    for message in messages:
        for call in getattr(message, "tool_calls", None) or []:
            if call.get("id") is not None:
                calls[call["id"]] = call

        call_id = getattr(message, "tool_call_id", None)
        if call_id is None:
            continue

        call = calls.get(call_id, {})
        args = ", ".join(f"{k}={v}" for k, v in (call.get("args") or {}).items())
        header = f"{call.get('name') or _UNKNOWN_TOOL}({args})"
        content = _text_of(message)
        if len(content) > max_chars:
            header += "  -- truncated, showing the first part only"
        blocks.append(f"{header}\n{content[:max_chars]}")

    return blocks


def _text_of(message: Any) -> str:
    """Return a message's text whatever shape its content arrived in."""
    text = getattr(message, "text", None)
    if isinstance(text, str):
        return text
    content = getattr(message, "content", "")
    return content if isinstance(content, str) else str(content)
