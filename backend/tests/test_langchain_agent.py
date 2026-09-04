"""Unit coverage for the deterministic LangChain/deepagents adapter."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any, cast

import pytest
from conftest import FakeGraph, FakeInterrupt, FakeStreamMessage, FakeToolCalls
from langchain_openai import ChatOpenAI
from langgraph.types import Command
from pydantic import SecretStr

from papyri_backend import langchain_agent as agent_module
from papyri_backend.exceptions import InvalidDecision, StaleDecision
from papyri_backend.langchain_agent import LangChainAgent


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


def _collect(events: Iterator[dict[str, Any]]) -> dict[str, Any]:
    """Apply wire deltas as the frontend adapter does."""
    result = {"text": "", "reasoning": "", "interrupt": None, "done": False}
    for event in events:
        if event["type"] in ("text", "reasoning"):
            result[event["type"]] += event["content"]
        elif event["type"] == "replace":
            result["text"] = event["content"]
        elif event["type"] == "done":
            result["interrupt"] = event["interrupt"]
            result["done"] = True
    result["text"] = result["text"].strip()
    result["reasoning"] = result["reasoning"].strip()
    return result


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


def test_turn_stream_yields_reasoning_and_text_deltas(user_message) -> None:
    graph = FakeGraph([FakeStreamMessage(text="Answer", reasoning="Plan")])
    agent = _agent(graph, thread_id="papyrus-thread")

    updates = list(agent.stream_single_turn(user_message("Question")))

    assert updates[0] == {"type": "reasoning", "content": "P"}
    assert (
        "".join(event["content"] for event in updates if event["type"] == "text")
        == "Answer"
    )
    assert _collect(iter(updates)) == {
        "text": "Answer",
        "reasoning": "Plan",
        "interrupt": None,
        "done": True,
    }
    assert graph.calls[0]["config"] == {"configurable": {"thread_id": "papyrus-thread"}}


def test_turn_stream_adds_finalized_tool_calls_to_reasoning(user_message) -> None:
    graph = FakeGraph(
        [
            FakeStreamMessage(
                text="Let me search more specifically.",
                tool_calls=FakeToolCalls(
                    [{"name": "query_sql", "args": {"tm_id": 123456}}]
                ),
            ),
            FakeStreamMessage(text="Here is the final answer."),
        ]
    )

    updates = list(_agent(graph).stream_single_turn(user_message("Question")))

    reasoning = "".join(
        event["content"] for event in updates if event["type"] == "reasoning"
    )
    assert "Let me search more specifically." in reasoning
    assert "Using tool: query_sql" in reasoning
    assert "tm_id: 123456" in reasoning
    assert (
        "".join(event["content"] for event in updates if event["type"] == "text")
        == "Here is the final answer."
    )


def test_turn_stream_accumulates_usage_across_model_calls(user_message) -> None:
    graph = FakeGraph(
        [
            FakeStreamMessage(
                text="I will search.",
                tool_calls=FakeToolCalls([{"name": "query_sql", "args": {}}]),
                usage_metadata={
                    "input_tokens": 120,
                    "output_tokens": 15,
                    "total_tokens": 135,
                    "input_token_details": {"cache_read": 80},
                },
            ),
            FakeStreamMessage(
                text="Here is the result.",
                usage_metadata={
                    "input_tokens": 180,
                    "output_tokens": 20,
                    "total_tokens": 200,
                    "input_token_details": {"cache_read": 120},
                },
            ),
        ]
    )

    agent = _agent(graph)
    agent.context_window = 1_000
    updates = list(agent.stream_single_turn(user_message("Question")))

    usage_updates = [event for event in updates if event["type"] == "usage"]
    assert usage_updates == [
        {
            "type": "usage",
            "usage": {
                "input_tokens": 120,
                "output_tokens": 15,
                "total_tokens": 135,
                "cached_input_tokens": 80,
            },
            "model_usage": {
                "model_call": 1,
                "input_tokens": 120,
                "output_tokens": 15,
                "total_tokens": 135,
                "cached_input_tokens": 80,
                "context_window": 1_000,
            },
        },
        {
            "type": "usage",
            "usage": {
                "input_tokens": 300,
                "output_tokens": 35,
                "total_tokens": 335,
                "cached_input_tokens": 200,
            },
            "model_usage": {
                "model_call": 2,
                "input_tokens": 180,
                "output_tokens": 20,
                "total_tokens": 200,
                "cached_input_tokens": 120,
                "context_window": 1_000,
            },
        },
    ]

    assert updates[-1] == {
        "type": "done",
        "interrupt": None,
        "usage": {
            "input_tokens": 300,
            "output_tokens": 35,
            "total_tokens": 335,
            "cached_input_tokens": 200,
        },
        "model_usage": usage_updates[-1]["model_usage"],
    }


def test_turn_usage_omits_aggregate_cache_when_any_call_lacks_details(
    user_message,
) -> None:
    graph = FakeGraph(
        [
            FakeStreamMessage(
                usage_metadata={
                    "input_tokens": 100,
                    "output_tokens": 10,
                    "total_tokens": 110,
                    "input_token_details": {"cache_read": 60},
                }
            ),
            FakeStreamMessage(
                text="Answer",
                usage_metadata={
                    "input_tokens": 150,
                    "output_tokens": 20,
                    "total_tokens": 170,
                },
            ),
        ]
    )

    updates = list(_agent(graph).stream_single_turn(user_message("Question")))
    usage_updates = [event for event in updates if event["type"] == "usage"]

    assert usage_updates[0]["usage"]["cached_input_tokens"] == 60
    assert "cached_input_tokens" not in usage_updates[1]["usage"]
    assert "cached_input_tokens" not in updates[-1]["usage"]


@pytest.mark.parametrize(
    ("profile", "expected"),
    [
        ({"max_input_tokens": 262_144}, 262_144),
        ({}, None),
        ({"max_input_tokens": 0}, None),
        ({"max_input_tokens": True}, None),
        (None, None),
    ],
)
def test_model_context_window(profile, expected) -> None:
    model = type("Model", (), {"profile": profile})()

    assert LangChainAgent._model_context_window(model) == expected


@pytest.mark.parametrize(
    "usage_metadata",
    [None, {}, {"input_tokens": 1, "output_tokens": 2}],
)
def test_turn_stream_omits_unavailable_or_incomplete_usage(
    user_message, usage_metadata
) -> None:
    graph = FakeGraph([FakeStreamMessage(text="Answer", usage_metadata=usage_metadata)])

    updates = list(_agent(graph).stream_single_turn(user_message("Question")))

    assert updates[-1] == {"type": "done", "interrupt": None}


@pytest.mark.parametrize(
    "text",
    ["<think>Plan</think>Answer", "  < THINK >Plan</ Think >Answer"],
)
def test_stream_reclassifies_chunked_inline_reasoning(user_message, text) -> None:
    graph = FakeGraph([FakeStreamMessage(text=text)])

    updates = list(_agent(graph).stream_single_turn(user_message("Question")))

    assert _collect(iter(updates)) == {
        "text": "Answer",
        "reasoning": "Plan",
        "interrupt": None,
        "done": True,
    }
    assert all("<think>" not in event.get("content", "") for event in updates)


def test_prefilled_reasoning_never_streams_as_answer_text(user_message) -> None:
    graph = FakeGraph([FakeStreamMessage(text="Plan</think>Answer")])
    agent = _agent(graph)
    agent.inline_reasoning = True

    updates = list(agent.stream_single_turn(user_message("Question")))

    assert _collect(iter(updates)) == {
        "text": "Answer",
        "reasoning": "Plan",
        "interrupt": None,
        "done": True,
    }
    assert all(
        event["type"] != "text" or "Plan" not in event["content"] for event in updates
    )


def test_raw_message_events_preserve_reasoning_and_text_deltas(user_message) -> None:
    class RawMessage:
        tool_calls = FakeToolCalls()

        def __iter__(self):
            return iter(
                [
                    {
                        "event": "content-block-delta",
                        "delta": {"type": "reasoning-delta", "reasoning": "R1"},
                    },
                    {
                        "event": "content-block-delta",
                        "delta": {"type": "text-delta", "text": "A1"},
                    },
                    {
                        "event": "content-block-delta",
                        "delta": {"type": "reasoning-delta", "reasoning": "R2"},
                    },
                    {
                        "event": "content-block-delta",
                        "delta": {"type": "text-delta", "text": "A2"},
                    },
                ]
            )

    graph = FakeGraph([RawMessage()])

    updates = list(_agent(graph).stream_single_turn(user_message("Question")))

    assert updates == [
        {"type": "reasoning", "content": "R1"},
        {"type": "reasoning", "content": "R2"},
        {"type": "text", "content": "A1"},
        {"type": "text", "content": "A2"},
        {"type": "done", "interrupt": None},
    ]


# --- complete turns and pauses ----------------------------------------------


def test_an_ordinary_turn_streams_an_answer(user_message) -> None:
    graph = FakeGraph([FakeStreamMessage(text="P.Oxy. XII 1450 is a lease.")])

    answer = _collect(_agent(graph).stream_single_turn(user_message("Find a lease.")))

    assert answer == {
        "text": "P.Oxy. XII 1450 is a lease.",
        "reasoning": "",
        "interrupt": None,
        "done": True,
    }


def test_an_empty_completed_run_returns_a_recoverable_message(user_message) -> None:
    """A completed turn without output must be visible to the chat user."""
    graph = FakeGraph([])

    answer = _collect(_agent(graph).stream_single_turn(user_message("Find a lease.")))

    assert answer == {
        "text": "No answer was produced. Please try again.",
        "reasoning": "",
        "interrupt": None,
        "done": True,
    }


def test_a_graph_failure_replaces_partial_output(user_message) -> None:
    graph = FakeGraph(
        [FakeStreamMessage(text="Partial answer", reasoning="Partial reasoning")],
        error_after_messages=RuntimeError("model failed"),
    )

    answer = _collect(_agent(graph).stream_single_turn(user_message("Find P.Oxy.")))

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

    answer = _collect(_agent(graph).stream_single_turn(user_message("Save the notes.")))

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

    answer = _collect(agent.stream_single_turn(decision_reply("interrupt-1")))

    payload = graph.calls[0]["payload"]
    assert isinstance(payload, Command)
    assert payload.resume == {"decisions": [{"type": "approve"}]}
    assert answer == {
        "text": "Saved.",
        "reasoning": "",
        "interrupt": None,
        "done": True,
    }


def test_an_allowed_rejection_resumes_and_clears_the_old_pause(decision_reply) -> None:
    interrupt = _interrupt(configs=[{"allowed_decisions": ["approve", "reject"]}])
    graph = FakeGraph(
        [FakeStreamMessage(text="I will not write the file.")], interrupts=[interrupt]
    )
    agent = _agent(graph)

    answer = _collect(
        agent.stream_single_turn(
            decision_reply(
                "interrupt-1", [{"type": "reject", "message": "do not save notes"}]
            )
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
        "done": True,
    }


def test_an_invalid_decision_does_not_run_or_clear_the_pause(decision_reply) -> None:
    interrupt = _interrupt(configs=[{"allowed_decisions": ["approve"]}])
    graph = FakeGraph(interrupts=[interrupt])
    agent = _agent(graph)

    with pytest.raises(InvalidDecision, match="not allowed"):
        agent.stream_single_turn(decision_reply("interrupt-1", [{"type": "reject"}]))

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
