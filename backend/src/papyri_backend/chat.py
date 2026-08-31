"""Answer chat requests with the current session's agent."""

from __future__ import annotations

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


async def answer_with_chat(raw_messages: list[Any]) -> dict[str, Any]:
    """Answer the latest message in a conversation.

    Args:
        raw_messages: The conversation so far. Only the last message is read;
            the rest is held by the agent's checkpointer.

    Returns:
        The agent's ``text`` answer, its ``reasoning`` trace and the
        ``interrupt`` it is now paused on, if any.

    Raises:
        DecisionError: The message answered an interrupt and was refused.
    """
    try:
        return session.current().agent.run_single_turn(raw_messages[-1])
    except DecisionError:
        # A refused decision carries a status code the transport turns into a
        # failed request, rather than being reported as agent output.
        raise
    except Exception as exc:
        # The session is dropped rather than reused, because a failed run can
        # leave the graph in a state the next turn cannot resume from.
        session.clear()
        return {
            "text": (
                f"Exception happened in chat: {exc}. "
                "Start a new session to clear the error"
            ),
            "reasoning": "",
            "interrupt": None,
        }
