"""Evidence is recovered from the message list with its provenance intact."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from papyri_backend.verification.evidence import (
    collect_evidence,
    format_evidence,
)


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

    items = collect_evidence(messages)

    assert len(items) == 1
    assert items[0].tool == "query_sql"
    assert items[0].args == {"query": "SELECT 1"}
    assert items[0].content == "tm_id\n8823"

def test_truncation_is_per_item_and_flagged() -> None:
    messages = [
        ai([{"id": "c1", "name": "query_sql", "args": {}}]),
        result("c1", "x" * 50),
        ai([{"id": "c2", "name": "query_sql", "args": {}}]),
        result("c2", "short"),
    ]

    items = collect_evidence(messages, max_chars=10)

    assert items[0].content == "x" * 10
    assert items[0].truncated is True
    assert items[1].content == "short"
    assert items[1].truncated is False

def test_messages_without_tools_produce_no_evidence() -> None:
    assert collect_evidence([human("hello")]) == []


def test_format_evidence_labels_each_block_with_its_call() -> None:
    items = collect_evidence(
        [
            ai([{"id": "c1", "name": "query_sql", "args": {"query": "SELECT 1"}}]),
            result("c1", "tm_id\n8823"),
        ]
    )

    rendered = format_evidence(items)

    assert rendered.startswith("[E1] query_sql(query=SELECT 1)")
    assert "8823" in rendered


def test_format_evidence_says_when_a_result_was_truncated() -> None:
    items = collect_evidence(
        [ai([{"id": "c1", "name": "query_sql", "args": {}}]), result("c1", "y" * 50)],
        max_chars=10,
    )

    assert "truncated" in format_evidence(items)


def test_format_evidence_states_plainly_when_nothing_was_retrieved() -> None:
    assert "No tools were called" in format_evidence([])