"""Recover what the agent actually retrieved, so a reviewer can check against it.

Today the evidence is read back out of the message list, by joining each
``ToolMessage`` to the tool call that produced it. When
``EvidenceLedgerMiddleware`` lands this module is the only thing that changes:
``collect_evidence`` reads ``state["evidence"]`` instead and returns the same
``EvidenceItem`` list, so the prompt, the contract, the middleware and their
tests are unaffected. That is the reason this indirection exists at all.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

_DEFAULT_MAX_CHARS = 4000 #can be changed based on more testing - just my prediction after some testing
_UNKNOWN_TOOL = "unknown" #name of the tool call can get missing after memory compression of the conversation


@dataclass(frozen=True)
class EvidenceItem:
    """One tool result, with the call that produced it.

    Shaped after the ledger record in the design so that the ledger can supply
    these directly later.
    """

    evidence_id: str
    tool: str
    args: dict[str, Any]
    content: str
    truncated: bool


def collect_evidence(
    messages: Sequence[Any], *, max_chars: int = _DEFAULT_MAX_CHARS
) -> list[EvidenceItem]:
    """Pair every tool result in a message list with the call that produced it.

    Args:
        messages: The conversation so far, oldest first.
        max_chars: Longest result text kept per item. Truncation is per item so
            that one very large result cannot crowd the others out of the
            reviewer's single model call.

    Returns:
        One item per tool result, numbered ``E1``, ``E2``, ... in call order.
    """
    # A ToolMessage carries the result and a tool_call_id, but not the tool's
    # name or arguments -- those are on the AIMessage that requested it
    calls: dict[str, dict[str, Any]] = {}
    items: list[EvidenceItem] = []

    for message in messages:
        for call in getattr(message, "tool_calls", None) or []:
            call_id = call.get("id")
            if call_id is not None:
                calls[call_id] = call

        call_id = getattr(message, "tool_call_id", None)
        if call_id is None:
            continue

        # Summarization can drop the requesting AIMessage while keeping itsresult.
        call = calls.get(call_id, {})
        content = _text_of(message)
        items.append(
            EvidenceItem(
                evidence_id=f"E{len(items) + 1}",
                tool=call.get("name") or _UNKNOWN_TOOL,
                args=call.get("args") or {},
                content=content[:max_chars],
                truncated=len(content) > max_chars,
            )
        )

    return items


def _text_of(message: Any) -> str:
    """Return a message's text whatever shape its content arrived in."""
    text = getattr(message, "text", None)
    if isinstance(text, str):
        return text
    content = getattr(message, "content", "")
    return content if isinstance(content, str) else str(content)


def format_evidence(items: Sequence[EvidenceItem]) -> str:
    """Render evidence for the reviewer's prompt.

    Args:
        items: The evidence, in call order.

    Returns:
        One labelled block per item, or a sentence stating that no tool was
        called -- which the reviewer needs to be able to distinguish from a
        missing section
    """
    if not items:
        return "No tools were called during this turn, so there is no evidence."

    blocks = []
    for item in items:
        args = ", ".join(f"{key}={value}" for key, value in item.args.items())
        header = f"[{item.evidence_id}] {item.tool}({args})"
        if item.truncated:
            header = f"{header}  -- truncated, showing the first part only"
        blocks.append(f"{header}\n{item.content}")

    return "\n\n".join(blocks)