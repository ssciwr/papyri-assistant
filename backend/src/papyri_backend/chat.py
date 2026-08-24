from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .exceptions import DecisionError
from .langchain_agent import (
    make_langchain_deepagent,
    make_langchain_retriever,
    LangChainAgent,
    RetrievalAgent,
)


agent: LangChainAgent | None = None
RETRIEVER: RetrievalAgent | None = None


async def new_agent() -> dict[str, str]:
    global agent
    global RETRIEVER
    try:
        # The retriever is not an agent of its own: it backs the search tools the
        # deep agent calls, which is what makes the agentic path a RAG one.
        RETRIEVER = make_langchain_retriever(
            os.getenv(
                "RETRIEVER_CONFIG",
                str(
                    Path(__file__).resolve().parents[2]
                    / os.getenv(
                        "RETRIEVER_CONFIG",
                        "configs/default_langchain_retriever.yaml",
                    )  # TODO: make this env var
                ),
            )
        )

        agent = make_langchain_deepagent(
            os.getenv(
                "AGENT_CONFIG",
                str(
                    Path(__file__).resolve().parents[2]
                    / os.getenv(
                        "AGENT_CONFIG", "configs/default_langchain_agent.yaml"
                    )  # TODO: make this env var
                ),
            )
        )
        return {"text": "DeepAgent has been restarted"}
    except Exception as e:
        return {
            "text": f"Exception happened in agent construction: {e}",
            "reasoning": "",
        }


async def answer_with_chat(raw_messages: list[Any]) -> dict[str, str]:

    # currently use a singleton agent b/c we only have a local usage

    if agent is None:
        await new_agent()

    try:
        answer = agent.run_single_turn(raw_messages[-1])
    except DecisionError:
        # A refused decision is a protocol error, not agent output: it carries a
        # status code the transport turns into a failed request.
        raise
    except Exception as e:
        answer = {"text": f"Exception happened in chat: {e}", "reasoning": ""}

    return answer
