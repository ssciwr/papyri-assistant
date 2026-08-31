"""Cover the chat layer: which agent answers, and what happens when it fails."""

from __future__ import annotations

import asyncio
from typing import Any, cast

import pytest

from papyri_backend import chat, session
from papyri_backend.exceptions import InvalidDecision, StaleDecision


class FakeAgent:
    def __init__(self, answer=None, error=None):
        self.answer = answer or {"text": "hi", "reasoning": "", "interrupt": None}
        self.error = error
        self.seen = []

    def run_single_turn(self, message):
        self.seen.append(message)
        if self.error is not None:
            raise self.error
        return self.answer


class FakeConnection:
    def __init__(self) -> None:
        self.close_calls = 0

    def close(self) -> None:
        self.close_calls += 1


def use(monkeypatch, agent) -> FakeConnection:
    """Install a session backed by the given fake agent."""
    connection = FakeConnection()
    fake = session.Session(
        agent=cast(Any, agent),
        retriever=cast(Any, object()),
        connection=cast(Any, connection),
    )
    monkeypatch.setattr(session, "_CURRENT", fake)
    return connection


def message(text: str) -> dict:
    return {"role": "user", "content": [{"type": "text", "text": text}]}


def test_only_the_latest_message_reaches_the_agent(monkeypatch) -> None:
    # The conversation lives in the agent's checkpointer, so resending the
    # history would replay it rather than continue it.
    agent = FakeAgent()
    use(monkeypatch, agent)

    asyncio.run(chat.answer_with_chat([message("first"), message("second")]))

    assert agent.seen == [message("second")]


def test_the_agents_answer_is_returned_unchanged(monkeypatch) -> None:
    answer = {"text": "hello", "reasoning": "thinking", "interrupt": None}
    use(monkeypatch, FakeAgent(answer=answer))

    assert asyncio.run(chat.answer_with_chat([message("hi")])) == answer


@pytest.mark.parametrize(
    "error",
    [StaleDecision("no decision pending"), InvalidDecision("decision not allowed")],
)
def test_a_refused_decision_is_raised_for_the_transport(monkeypatch, error) -> None:
    # A decision-protocol error carries a status code, not agent output, so it
    # must not be flattened into a chat answer.
    use(monkeypatch, FakeAgent(error=error))

    with pytest.raises(type(error)):
        asyncio.run(chat.answer_with_chat([message("{}")]))


def test_an_empty_conversation_is_reported_as_a_chat_error(monkeypatch) -> None:
    use(monkeypatch, FakeAgent())

    answer = asyncio.run(chat.answer_with_chat([]))

    assert answer["text"].startswith("Exception happened in chat:")
    assert answer["reasoning"] == ""
    assert answer["interrupt"] is None
    assert session._CURRENT is None


@pytest.mark.parametrize(
    "raw_message",
    [{}, {"content": []}, {"content": [{}]}],
    ids=["missing-content", "empty-content", "missing-text"],
)
def test_malformed_last_messages_are_forwarded_to_the_agent(
    monkeypatch, raw_message
) -> None:
    agent = FakeAgent()
    use(monkeypatch, agent)

    answer = asyncio.run(chat.answer_with_chat([raw_message]))

    assert answer == agent.answer
    assert agent.seen == [raw_message]


def test_a_failed_run_is_reported_as_chat_output(monkeypatch) -> None:
    use(monkeypatch, FakeAgent(error=RuntimeError("provider exploded")))

    answer = asyncio.run(chat.answer_with_chat([message("hi")]))

    assert "provider exploded" in answer["text"]
    # The shape has to match a successful answer, because the client reads the
    # same fields either way.
    assert set(answer) == {"text", "reasoning", "interrupt"}


def test_a_failed_run_drops_the_session(monkeypatch) -> None:
    # A failed run can leave the graph in a state the next turn cannot resume
    # from, so the next request starts a fresh agent rather than reusing it.
    connection = use(monkeypatch, FakeAgent(error=RuntimeError("boom")))

    asyncio.run(chat.answer_with_chat([message("hi")]))

    assert session._CURRENT is None
    assert connection.close_calls == 1


def test_new_agent_starts_a_session(monkeypatch) -> None:
    started = []
    monkeypatch.setattr(session, "start", lambda: started.append(True))

    answer = chat.new_agent()

    assert started == [True]
    assert answer["text"]
