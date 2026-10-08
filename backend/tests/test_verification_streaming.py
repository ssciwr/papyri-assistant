"""A rejected answer never reaches the browser.

The reviewer runs at the end of the graph run, so answer text has to be held
back until then: whether it survives review is not known while it is being
produced, and a stream cannot be recalled.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from conftest import FakeGraph, FakeStreamMessage, FakeToolCalls

from papyri_backend.langchain_agent import LangChainAgent


def agent_over(
    graph: FakeGraph, report: dict[str, Any] | None = None
) -> LangChainAgent:
    """An adapter shell over a fake graph, optionally carrying a report.

    ``FakeGraph``'s state fake exposes only ``interrupts``; ``_review_report``
    reads ``values``, so the state is replaced with one carrying both.
    """
    agent = object.__new__(LangChainAgent)
    agent.agent = cast(Any, graph)
    agent.thread_id = "verification-thread"
    graph.states["default"] = cast(
        Any,
        SimpleNamespace(
            interrupts=[],
            values={"review_report": report} if report is not None else {},
        ),
    )
    return agent


def question() -> dict[str, Any]:
    return {"role": "user", "content": [{"type": "text", "text": "Find a lease."}]}


def tool_message(text: str, name: str) -> FakeStreamMessage:
    """A message whose text accompanies a tool call, so it is reasoning."""
    return FakeStreamMessage(
        text=text,
        tool_calls=FakeToolCalls([{"name": name, "args": {"query": "lease"}}]),
    )


def events_of(agent: LangChainAgent) -> list[dict[str, Any]]:
    return list(agent.stream_single_turn(question()))


def texts(events: list[dict[str, Any]]) -> list[str]:
    return [event["content"] for event in events if event["type"] == "text"]


def test_one_answer_is_emitted_once_and_after_the_reasoning() -> None:
    graph = FakeGraph(
        [
            tool_message("Let me search.", "similarity_search"),
            FakeStreamMessage(text="P.Oxy. 1450 is a house lease."),
        ]
    )

    events = events_of(agent_over(graph))
    kinds = [event["type"] for event in events]

    assert texts(events) == ["P.Oxy. 1450 is a house lease."]
    assert kinds.index("reasoning") < kinds.index("text")


def test_only_the_surviving_answer_reaches_the_browser() -> None:
    # The reviewer rejected the first answer and the graph produced a second.
    graph = FakeGraph(
        [
            FakeStreamMessage(text="Fishing was common in Roman Egypt."),
            FakeStreamMessage(text="47 documents mention fishing."),
        ]
    )

    events = events_of(agent_over(graph))

    assert texts(events) == ["47 documents mention fishing."]
    assert "Fishing was common" not in "".join(texts(events))


def test_the_internal_answer_event_is_never_forwarded() -> None:
    # "answer" is the buffering channel between _stream_drive and this method.
    # Letting it reach the wire would break the frontend, which raises on an
    # event type it does not know.
    graph = FakeGraph([FakeStreamMessage(text="Two documents do.")])

    kinds = [event["type"] for event in events_of(agent_over(graph))]

    assert "answer" not in kinds


def test_the_report_is_carried_to_the_browser_before_done() -> None:
    report = {"verdict": "pass", "retries": 0, "evidence_count": 2, "parsed": True}
    graph = FakeGraph([FakeStreamMessage(text="Two documents do.")])

    events = events_of(agent_over(graph, report))
    kinds = [event["type"] for event in events]

    assert events[kinds.index("verification")]["verification"] == report
    assert kinds.index("verification") < kinds.index("done")


def test_no_report_is_emitted_when_no_reviewer_is_configured() -> None:
    # default_langchain_agent.yaml has no reviewer, so the event is optional.
    graph = FakeGraph([FakeStreamMessage(text="Two documents do.")])

    kinds = [event["type"] for event in events_of(agent_over(graph))]

    assert "verification" not in kinds
