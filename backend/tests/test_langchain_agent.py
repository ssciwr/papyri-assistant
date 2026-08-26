"""Unit coverage for the deterministic LangChain/deepagents adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
from conftest import FakeGraph, FakeInterrupt, FakeStreamMessage, FakeToolCalls
from langchain_openai import ChatOpenAI
from langgraph.types import Command
from pydantic import SecretStr

from papyri_backend import langchain_agent as agent_module
from papyri_backend.exceptions import InvalidDecision, StaleDecision
from papyri_backend.langchain_agent import LangChainAgent, TurnOutput


def _agent(graph: FakeGraph, thread_id: str = "test-thread") -> LangChainAgent:
    """Build an adapter shell around a fake graph without constructing a model."""
    agent = object.__new__(LangChainAgent)
    agent.agent = cast(Any, graph)
    agent.thread_id = thread_id
    return agent


def _interrupt(
    interrupt_id: str = "interrupt-1",
    actions: list[dict[str, Any]] | None = None,
    configs: list[dict[str, Any]] | None = None,
) -> FakeInterrupt:
    return FakeInterrupt(
        id=interrupt_id,
        value={
            "action_requests": actions
            or [{"name": "write_file", "args": {"file_path": "/workspace/a.md"}}],
            "review_configs": configs
            or [{"allowed_decisions": ["approve", "edit", "reject", "respond"]}],
        },
    )


# --- construction and configuration -----------------------------------------


def test_construction_works() -> None:
    """A usable agent can be assembled without contacting its model provider."""
    agent = LangChainAgent(
        model=ChatOpenAI(
            model="test-model",
            base_url="http://localhost:9999/v1",
            api_key=SecretStr("test-key"),
        ),
        tools=[],
    )

    assert agent.agent is not None
    assert agent.thread_id
    assert agent._pending_interrupt() is None


def test_each_constructed_agent_gets_a_distinct_thread_id(monkeypatch) -> None:
    monkeypatch.setattr(agent_module.utils, "build", lambda value, _deps=None: value)
    monkeypatch.setattr(
        agent_module, "create_deep_agent", lambda **_kwargs: FakeGraph()
    )

    first = LangChainAgent(model=object(), tools=[])
    second = LangChainAgent(model=object(), tools=[])

    assert first.thread_id != second.thread_id
    assert first._config == {"configurable": {"thread_id": first.thread_id}}


def test_from_config_loads_and_delegates_to_the_constructor(monkeypatch) -> None:
    config = {"model": "configured-model", "tools": []}
    received: dict[str, object] = {}

    monkeypatch.setattr(agent_module.utils, "load_config", lambda path: config)
    monkeypatch.setattr(
        LangChainAgent,
        "__init__",
        lambda _self, **kwargs: received.update(kwargs),
    )

    result = LangChainAgent.from_config(Path("agent.yaml"))

    assert isinstance(result, LangChainAgent)
    assert received == config


# --- streaming ---------------------------------------------------------------


def test_drive_collects_messages_and_uses_the_v3_thread_config() -> None:
    graph = FakeGraph(
        [
            FakeStreamMessage(text="First ", reasoning="Plan: "),
            FakeStreamMessage(
                text="answer",
                tool_calls=FakeToolCalls(
                    [{"name": "query_sql", "args": {"tm_id": 123456}}]
                ),
            ),
        ]
    )
    agent = _agent(graph, thread_id="papyrus-thread")
    turn = TurnOutput()

    agent._drive({"messages": []}, turn)

    assert turn.answer == "First answer"
    assert "Plan:" in turn.reasoning
    assert "Using tool: query_sql" in turn.reasoning
    assert graph.calls == [
        {
            "payload": {"messages": []},
            "config": {"configurable": {"thread_id": "papyrus-thread"}},
            "version": "v3",
        }
    ]


def test_drive_propagates_graph_failures_to_its_caller() -> None:
    graph = FakeGraph(error=RuntimeError("stream disconnected"))

    with pytest.raises(RuntimeError, match="stream disconnected"):
        _agent(graph)._drive({"messages": []}, TurnOutput())


# --- complete turns and pauses ----------------------------------------------


def test_an_ordinary_turn_streams_an_answer(user_message) -> None:
    graph = FakeGraph([FakeStreamMessage(text="P.Oxy. XII 1450 is a lease.")])

    answer = _agent(graph).run_single_turn(user_message("Find a lease."))

    assert answer == {
        "text": "P.Oxy. XII 1450 is a lease.",
        "reasoning": "",
        "interrupt": None,
    }


def test_an_empty_completed_run_returns_a_recoverable_message(user_message) -> None:
    """A completed turn without output must be visible to the chat user."""
    graph = FakeGraph([])

    answer = _agent(graph).run_single_turn(user_message("Find a lease."))

    assert answer == {
        "text": "The agent returned an empty or unknown answer. Please try again.",
        "reasoning": "",
        "interrupt": None,
    }


def test_a_graph_failure_replaces_partial_output(user_message) -> None:
    graph = FakeGraph(
        [FakeStreamMessage(text="Partial answer", reasoning="Partial reasoning")],
        error_after_messages=RuntimeError("model failed"),
    )

    answer = _agent(graph).run_single_turn(user_message("Find P.Oxy."))

    assert answer["text"] == "The agent run failed: model failed"
    assert answer["reasoning"] == "Partial reasoning"


def test_a_paused_turn_includes_an_action_specific_client_view(user_message) -> None:
    interrupt = _interrupt(
        actions=[{"name": "write_file", "args": {"file_path": "/workspace/a.md"}}],
        configs=[{"allowed_decisions": ["approve", "reject"]}],
    )
    graph = FakeGraph(
        [FakeStreamMessage(text="I will save the notes.\n")], interrupts=[interrupt]
    )

    answer = _agent(graph).run_single_turn(user_message("Save the notes."))

    assert (
        answer["text"]
        == "I will save the notes.\nPlease decide how you want to proceed:"
    )
    assert answer["interrupt"] == {
        "id": "interrupt-1",
        "actions": [
            {
                "name": "write_file",
                "args": {"file_path": "/workspace/a.md"},
                "allowed_decisions": ["approve", "reject"],
            }
        ],
    }


def test_a_valid_decision_resumes_the_paused_turn(decision_reply) -> None:
    interrupt = _interrupt()
    graph = FakeGraph([FakeStreamMessage(text="Saved.")], interrupts=[interrupt])
    agent = _agent(graph)

    answer = agent.run_single_turn(decision_reply("interrupt-1"))

    payload = graph.calls[0]["payload"]
    assert isinstance(payload, Command)
    assert payload.resume == {"decisions": [{"type": "approve"}]}
    assert answer == {"text": "Saved.", "reasoning": "", "interrupt": None}


def test_an_allowed_rejection_resumes_and_clears_the_old_pause(decision_reply) -> None:
    interrupt = _interrupt(configs=[{"allowed_decisions": ["approve", "reject"]}])
    graph = FakeGraph(
        [FakeStreamMessage(text="I will not write the file.")], interrupts=[interrupt]
    )
    agent = _agent(graph)

    answer = agent.run_single_turn(
        decision_reply(
            "interrupt-1", [{"type": "reject", "message": "do not save notes"}]
        )
    )

    payload = graph.calls[0]["payload"]
    assert isinstance(payload, Command)
    assert payload.resume == {
        "decisions": [{"type": "reject", "message": "do not save notes"}]
    }
    assert agent._pending_interrupt() is None
    assert answer == {
        "text": "I will not write the file.",
        "reasoning": "",
        "interrupt": None,
    }


def test_an_invalid_decision_does_not_run_or_clear_the_pause(decision_reply) -> None:
    interrupt = _interrupt(configs=[{"allowed_decisions": ["approve"]}])
    graph = FakeGraph(interrupts=[interrupt])
    agent = _agent(graph)

    with pytest.raises(InvalidDecision, match="not allowed"):
        agent.run_single_turn(decision_reply("interrupt-1", [{"type": "reject"}]))

    assert graph.calls == []
    assert agent._pending_interrupt() is interrupt


# --- resume protocol ---------------------------------------------------------


def test_resuming_without_a_pause_is_stale() -> None:
    with pytest.raises(StaleDecision, match="No decision"):
        _agent(FakeGraph())._resume_command({"interrupt_id": "interrupt-1"})


def test_resuming_another_interrupt_is_stale() -> None:
    graph = FakeGraph(interrupts=[_interrupt()])

    with pytest.raises(StaleDecision, match="no longer pending"):
        _agent(graph)._resume_command({"interrupt_id": "stale", "decisions": []})


def test_decision_count_must_match_paused_actions() -> None:
    graph = FakeGraph(
        interrupts=[_interrupt(actions=[{"name": "write_file"}, {"name": "delete"}])]
    )

    with pytest.raises(InvalidDecision, match="Expected 2 decisions, got 1"):
        _agent(graph)._resume_command(
            {"interrupt_id": "interrupt-1", "decisions": [{"type": "approve"}]}
        )


@pytest.mark.parametrize(
    ("reply", "expected"),
    [
        ({"type": "approve"}, {"type": "approve"}),
        (
            {"type": "edit", "args": {"file_path": "/workspace/edited.md"}},
            {
                "type": "edit",
                "edited_action": {
                    "name": "write_file",
                    "args": {"file_path": "/workspace/edited.md"},
                },
            },
        ),
        (
            {"type": "reject", "message": "  choose another path  "},
            {"type": "reject", "message": "choose another path"},
        ),
        ({"type": "reject"}, {"type": "reject"}),
        (
            {"type": "respond", "message": "use the cited source"},
            {"type": "respond", "message": "use the cited source"},
        ),
    ],
)
def test_resume_translates_every_supported_decision(reply, expected) -> None:
    graph = FakeGraph(interrupts=[_interrupt()])

    command = _agent(graph)._resume_command(
        {"interrupt_id": "interrupt-1", "decisions": [reply]}
    )

    assert command.resume == {"decisions": [expected]}


def test_resume_rejects_a_disallowed_decision_for_its_specific_action() -> None:
    graph = FakeGraph(
        interrupts=[
            _interrupt(
                actions=[{"name": "read_file"}],
                configs=[{"allowed_decisions": ["respond"]}],
            )
        ]
    )

    with pytest.raises(InvalidDecision, match="read_file"):
        _agent(graph)._resume_command(
            {"interrupt_id": "interrupt-1", "decisions": [{"type": "approve"}]}
        )


@pytest.mark.parametrize(
    "reply",
    [
        {"type": "edit"},
        {"type": "respond"},
        {"type": "respond", "message": "   "},
    ],
)
def test_resume_rejects_decision_bodies_missing_required_data(reply) -> None:
    graph = FakeGraph(interrupts=[_interrupt()])

    with pytest.raises(InvalidDecision):
        _agent(graph)._resume_command(
            {"interrupt_id": "interrupt-1", "decisions": [reply]}
        )


def test_multiple_actions_resume_in_request_order() -> None:
    graph = FakeGraph(
        interrupts=[
            _interrupt(
                actions=[
                    {"name": "write_file", "args": {"file_path": "/workspace/a.md"}},
                    {"name": "read_file", "args": {"file_path": "/workspace/b.md"}},
                ],
                configs=[
                    {"allowed_decisions": ["approve"]},
                    {"allowed_decisions": ["respond"]},
                ],
            )
        ]
    )

    command = _agent(graph)._resume_command(
        {
            "interrupt_id": "interrupt-1",
            "decisions": [
                {"type": "approve"},
                {"type": "respond", "message": "read the lease first"},
            ],
        }
    )

    assert command.resume == {
        "decisions": [
            {"type": "approve"},
            {"type": "respond", "message": "read the lease first"},
        ]
    }


def test_non_object_decision_json_is_treated_as_an_ordinary_question() -> None:
    assert LangChainAgent._as_decision('[{"interrupt_id": "nope"}]') is None
    assert LangChainAgent._as_decision('{"interrupt_id": null, "decisions": []}') == {
        "interrupt_id": None,
        "decisions": [],
    }
