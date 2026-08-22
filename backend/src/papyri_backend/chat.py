from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .exceptions import DecisionError
from .langchain_agent import create_agent_from_config as make_langchain_agent

_DEFAULT_SYSTEM_PROMPT = "You are a concise, helpful assistant."
_MAX_CONTEXT_MESSAGES = 9


agent = None


async def answer_with_chat(raw_messages: list[Any]) -> dict[str, str]:

    # currently use a singleton agent b/c we only have a local usage
    global agent
    if agent is None:
        try:
            agent = make_langchain_agent(
                os.getenv(
                    "AGENT_CONFIG",
                    str(
                        Path(__file__).resolve().parents[2]
                        / "configs/default_langchain_agent.yaml"
                    ),
                )
            )
        except Exception as e:
            return {
                "text": f"Exception happened in agent construction: {e}",
                "reasoning": "",
            }

    try:
        answer = agent.run_single_turn(raw_messages[-1])
    except DecisionError:
        # A refused decision is a protocol error, not agent output: it carries a
        # status code the transport turns into a failed request.
        raise
    except Exception as e:
        answer = {"text": f"Exception happened in chat: {e}", "reasoning": ""}

    return answer
