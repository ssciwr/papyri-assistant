"""Answer chat requests with the current session's agent."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from . import session
from .exceptions import DecisionError


def new_agent() -> dict[str, str]:
    """Start a fresh session, discarding the current conversation.

    Returns:
        A chat answer confirming the restart.
    """
    session.start()
    return {"text": "DeepAgent has been restarted"}


def answer_with_chat_stream(raw_messages: list[Any]) -> Iterator[dict[str, Any]]:
    """Return a guarded stream for the latest conversation message.

    Creating the agent iterator is deliberately eager so decision errors can
    be translated to an HTTP status before response headers are sent.
    """
    try:
        stream = session.current().agent.stream_single_turn(raw_messages[-1])
    except DecisionError:
        raise
    except Exception as exc:
        session.clear()
        return iter(
            (
                {
                    "text": (
                        f"Exception happened in chat: {exc}. "
                        "Start a new session to clear the error"
                    ),
                    "reasoning": "",
                    "interrupt": None,
                    "done": True,
                },
            )
        )

    return _guard_stream(stream)


def _guard_stream(stream: Iterator[dict[str, Any]]) -> Iterator[dict[str, Any]]:
    """Drop a possibly corrupted session if iteration fails unexpectedly."""
    try:
        yield from stream
    except GeneratorExit:
        # A disconnected browser can leave the graph between checkpoints.
        # Do not reuse that partially consumed run for the next request.
        session.clear()
        raise
    except Exception as exc:
        session.clear()
        yield {
            "text": (
                f"Exception happened in chat: {exc}. "
                "Start a new session to clear the error"
            ),
            "reasoning": "",
            "interrupt": None,
            "done": True,
        }
