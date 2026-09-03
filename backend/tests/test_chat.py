"""Cover the chat layer: which agent answers, and what happens when it fails."""

from __future__ import annotations

from typing import Any, cast

import pytest

from papyri_backend import chat, session
from papyri_backend.exceptions import InvalidDecision, StaleDecision


class FakeStreamingAgent:
    def __init__(self, updates=(), error=None, deferred_error=None):
        self.updates = list(updates)
        self.error = error
        self.deferred_error = deferred_error
        self.seen = []

    def stream_single_turn(self, message):
        self.seen.append(message)
        if self.error is not None:
            raise self.error

        def stream():
            yield from self.updates
            if self.deferred_error is not None:
                raise self.deferred_error

        return stream()


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


def test_new_agent_starts_a_session(monkeypatch) -> None:
    started = []
    monkeypatch.setattr(session, "start", lambda: started.append(True))

    answer = chat.new_agent()

    assert started == [True]
    assert answer["text"]


def test_stream_forwards_every_update_from_the_latest_message(monkeypatch) -> None:
    updates = [
        {"text": "", "reasoning": "Plan", "interrupt": None, "done": False},
        {"text": "Done", "reasoning": "Plan", "interrupt": None, "done": True},
    ]
    agent = FakeStreamingAgent(updates)
    use(monkeypatch, agent)

    result = list(chat.answer_with_chat_stream([message("first"), message("second")]))

    assert result == updates
    assert agent.seen == [message("second")]


@pytest.mark.parametrize(
    "error",
    [StaleDecision("no decision pending"), InvalidDecision("decision not allowed")],
)
def test_stream_raises_eager_decision_errors(monkeypatch, error) -> None:
    use(monkeypatch, FakeStreamingAgent(error=error))

    with pytest.raises(type(error)):
        chat.answer_with_chat_stream([message("decision")])


def test_stream_failure_becomes_a_terminal_update_and_drops_session(
    monkeypatch,
) -> None:
    connection = use(
        monkeypatch,
        FakeStreamingAgent(deferred_error=RuntimeError("stream disconnected")),
    )

    result = list(chat.answer_with_chat_stream([message("hi")]))

    assert result[-1]["done"] is True
    assert "stream disconnected" in result[-1]["text"]
    assert session._CURRENT is None
    assert connection.close_calls == 1


def test_closing_a_stream_drops_the_partially_consumed_session(monkeypatch) -> None:
    connection = use(
        monkeypatch,
        FakeStreamingAgent(
            [
                {
                    "text": "partial",
                    "reasoning": "",
                    "interrupt": None,
                    "done": False,
                }
            ]
        ),
    )
    stream = chat.answer_with_chat_stream([message("hi")])

    next(stream)
    stream.close()

    assert session._CURRENT is None
    assert connection.close_calls == 1
