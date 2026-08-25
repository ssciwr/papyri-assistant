"""Cover how one turn's model messages become a chat answer."""

from __future__ import annotations

import pytest

from papyri_backend.langchain_agent import TurnOutput, split_think


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param(
            "<think>weighing it</think>The answer.",
            ("weighing it", "The answer."),
            id="both-tags",
        ),
        pytest.param(
            "pre-filled trace</think>The answer.",
            ("pre-filled trace", "The answer."),
            id="opening-tag-prefilled-by-template",
        ),
        pytest.param(
            "< THINK >trace</ Think >The answer.",
            ("trace", "The answer."),
            id="spacing-and-casing-vary-by-deployment",
        ),
        pytest.param("Just the answer.", ("", "Just the answer."), id="no-trace"),
        pytest.param("", ("", ""), id="empty"),
    ],
)
def test_split_think(text: str, expected: tuple[str, str]) -> None:
    assert split_think(text) == expected


def test_a_trace_is_kept_out_of_the_answer() -> None:
    turn = TurnOutput()
    turn.add_message("<think>reasoning</think>Answer.", "", [])

    assert turn.as_answer(None) == {
        "text": "Answer.",
        "reasoning": "reasoning",
        "interrupt": None,
    }


def test_separately_reported_reasoning_is_collected() -> None:
    # A model that emits reasoning as its own stream rather than inline.
    turn = TurnOutput()
    turn.add_message("Answer.", "reasoning", [])

    assert turn.as_answer(None)["reasoning"] == "reasoning"


def test_a_tool_call_between_two_reasoning_messages_stays_in_the_trace() -> None:
    # The mainline path for this agent: a reasoning model that calls a tool.
    # The tool calls belong to the trace rather than to the answer, which is
    # what the user reads, and the answer text around them stays out of it.
    turn = TurnOutput()
    turn.add_message(
        "<think>step one</think>Let me look that up.",
        "",
        [{"name": "query_sql", "args": {"query": "select 1"}}],
    )
    turn.add_message("<think>step two</think>Done.", "", [])

    answer = turn.as_answer(None)

    assert "Let me look that up." in answer["text"]
    assert "Done." in answer["text"]
    assert "Using tool: query_sql" not in answer["text"]
    assert "Using tool: query_sql" in answer["reasoning"]
    assert "step one" in answer["reasoning"]
    assert "step two" in answer["reasoning"]
    assert "Let me look that up." not in answer["reasoning"]


def test_an_error_replaces_a_partial_answer() -> None:
    # A failed run leaves no usable answer, and what it did emit is typically a
    # tool-call announcement rather than anything the user asked for.
    turn = TurnOutput()
    turn.add_message("", "", [{"name": "query_sql", "args": {}}])
    turn.error = "The agent run failed: boom"

    assert turn.as_answer(None)["text"] == "The agent run failed: boom"


def test_the_interrupt_is_carried_through() -> None:
    turn = TurnOutput()
    turn.add_message("Awaiting approval.", "", [])
    view = {"id": "abc", "actions": []}

    assert turn.as_answer(view)["interrupt"] is view
