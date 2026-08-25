"""Cover the decision protocol a paused run is answered through.

Decisions travel as the JSON text of an ordinary chat message, so the parsing
and the translation into what the graph expects are pure functions over that
text. The frontend mirrors this protocol in decisionGate.ts.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from papyri_backend.exceptions import InvalidDecision
from papyri_backend.langchain_agent import LangChainAgent

as_decision = LangChainAgent._as_decision
build_decision = LangChainAgent._build_decision
interrupt_view = LangChainAgent._interrupt_view


# --- reading a message as a decision ----------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("What does P.Oxy. 1 say?", id="prose"),
        pytest.param("{not json", id="unparseable"),
        pytest.param('{"type": "approve"}', id="json-without-interrupt-id"),
        pytest.param('["approve"]', id="json-array"),
        pytest.param("", id="empty"),
    ],
)
def test_an_ordinary_message_is_not_a_decision(text: str) -> None:
    # Every message is examined, so anything a user might plausibly type has to
    # come back as ordinary chat rather than being read as a protocol message.
    assert as_decision(text) is None


def test_a_decision_reply_is_recognised() -> None:
    payload = as_decision('{"interrupt_id": "abc", "decisions": [{"type": "approve"}]}')

    assert payload == {"interrupt_id": "abc", "decisions": [{"type": "approve"}]}


# --- translating one reply into a decision ----------------------------------

ACTION = {"name": "write_file", "args": {"file_path": "/workspace/a.md"}}
CONFIG = {"allowed_decisions": ["approve", "edit", "reject", "respond"]}


def test_approve() -> None:
    assert build_decision({"type": "approve"}, ACTION, CONFIG) == {"type": "approve"}


def test_a_decision_the_action_does_not_allow_is_refused() -> None:
    with pytest.raises(InvalidDecision, match="not allowed"):
        build_decision({"type": "edit"}, ACTION, {"allowed_decisions": ["approve"]})


def test_a_missing_type_is_refused() -> None:
    with pytest.raises(InvalidDecision):
        build_decision({}, ACTION, CONFIG)


def test_an_edit_takes_its_name_from_the_paused_action() -> None:
    # The reply cannot redirect the decision at a different tool, so the name is
    # read from what was paused rather than from what the client sent.
    decision = build_decision(
        {"type": "edit", "args": {"file_path": "/workspace/b.md"}, "name": "delete"},
        ACTION,
        CONFIG,
    )

    assert decision == {
        "type": "edit",
        "edited_action": {
            "name": "write_file",
            "args": {"file_path": "/workspace/b.md"},
        },
    }


def test_an_edit_without_args_is_refused() -> None:
    with pytest.raises(InvalidDecision, match="args"):
        build_decision({"type": "edit", "args": "nope"}, ACTION, CONFIG)


def test_a_reject_may_carry_a_reason() -> None:
    # The reason reaches the model as the refused call's result, which is how it
    # learns what to do instead.
    assert build_decision(
        {"type": "reject", "message": " wrong path "}, ACTION, CONFIG
    ) == {
        "type": "reject",
        "message": "wrong path",
    }


def test_a_reject_without_a_reason_is_allowed() -> None:
    assert build_decision({"type": "reject"}, ACTION, CONFIG) == {"type": "reject"}


def test_responding_on_behalf_of_a_tool_needs_a_message() -> None:
    # An empty response would reach the model as an empty tool result, which
    # tells it nothing about why the call did not run.
    with pytest.raises(InvalidDecision, match="message"):
        build_decision({"type": "respond", "message": "   "}, ACTION, CONFIG)


def test_respond_carries_its_message() -> None:
    assert build_decision(
        {"type": "respond", "message": "use the db"}, ACTION, CONFIG
    ) == {
        "type": "respond",
        "message": "use the db",
    }


# --- describing a pause to the client ---------------------------------------


def test_an_interrupt_is_described_action_by_action() -> None:
    interrupt = SimpleNamespace(
        id="abc",
        value={
            "action_requests": [
                {"name": "write_file", "args": {"file_path": "/workspace/a.md"}},
                {"name": "delete"},
            ],
            "review_configs": [
                {"allowed_decisions": ["approve", "reject"]},
                {"allowed_decisions": ["approve"]},
            ],
        },
    )

    assert interrupt_view(interrupt) == {
        "id": "abc",
        "actions": [
            {
                "name": "write_file",
                "args": {"file_path": "/workspace/a.md"},
                "allowed_decisions": ["approve", "reject"],
            },
            # An action with no arguments still needs an args object, because
            # the client renders one form per action.
            {"name": "delete", "args": {}, "allowed_decisions": ["approve"]},
        ],
    }
