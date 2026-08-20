from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any
from pathlib import Path

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from .utils.messages import NormalizedMessage, normalize_messages
from .langchain_agent import LangChainAgent
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
            answer_text = f"Exception happened in agent construction: {e}"

    try:
        answer = agent.run_single_turn(raw_messages[-1])
    except Exception as e:
        answer = {"text": f"Exception happened in chat: {e}", "reasoning": ""}

    return {"text": answer["text"], "reasoning": answer["reasoning"]}
