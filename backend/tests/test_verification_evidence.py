"""Evidence is recovered from the message list with its provenance intact."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from papyri_backend.verification.evidence import evidence_blocks


def ai(tool_calls: list[dict[str, Any]]) -> Any:
    """An assistant message requesting tool calls."""
    return SimpleNamespace(tool_calls=tool_calls, content="", tool_call_id=None)


def result(call_id: str, content: str) -> Any:
    """A tool result message."""
    return SimpleNamespace(tool_call_id=call_id, content=content, tool_calls=None)


def human(text: str) -> Any:
    return SimpleNamespace(content=text, tool_calls=None, tool_call_id=None)


def test_a_tool_result_is_rejoined_with_its_call() -> None:
    messages = [
        human("Which documents mention Sarapion?"),
        ai([{"id": "c1", "name": "query_sql", "args": {"query": "SELECT 1"}}]),
        result("c1", "tm_id\n8823"),
    ]

    blocks = evidence_blocks(messages, max_chars=1000)

    assert blocks == ["query_sql(query=SELECT 1)\ntm_id\n8823"]


def test_truncation_is_per_result_and_flagged() -> None:
    messages = [
        ai([{"id": "c1", "name": "query_sql", "args": {}}]),
        result("c1", "x" * 50),
        ai([{"id": "c2", "name": "query_sql", "args": {}}]),
        result("c2", "short"),
    ]

    blocks = evidence_blocks(messages, max_chars=10)

    assert blocks[0] == (
        "query_sql()  -- truncated, showing the first part only\n" + "x" * 10
    )
    assert blocks[1] == "query_sql()\nshort"


def test_messages_without_tools_produce_no_evidence() -> None:
    assert evidence_blocks([human("hello")], max_chars=1000) == []


def test_a_result_whose_call_was_summarized_away_is_still_evidence() -> None:
    blocks = evidence_blocks([result("gone", "8823")], max_chars=1000)

    assert blocks == ["unknown()\n8823"]
