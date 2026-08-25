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


AGENT: LangChainAgent | None = None
RETRIEVER: RetrievalAgent | None = None


def new_agent() -> dict[str, str]:
    global AGENT
    global RETRIEVER
    try:
        AGENT = make_langchain_deepagent(
            os.getenv(
                "AGENT_CONFIG",
                str(
                    Path(__file__).resolve().parents[2]
                    / os.getenv("AGENT_CONFIG", "configs/default_langchain_agent.yaml")
                ),
            )
        )

        # The retriever is not an AGENT of its own: it backs the search tools the
        # deep AGENT calls, which is what makes the agentic path into RAG.
        RETRIEVER = make_langchain_retriever(
            os.getenv(
                "RETRIEVER_CONFIG",
                str(
                    Path(__file__).resolve().parents[2]
                    / os.getenv(
                        "RETRIEVER_CONFIG",
                        "configs/default_langchain_retriever.yaml",
                    )
                ),
            )
        )
    except Exception as e:
        raise RuntimeError(f"Error during agent construction: {e}") from e

    if AGENT is None or RETRIEVER is None:
        raise ValueError("Error, Agents have not been constructed")
    return {"text": "DeepAgent has been restarted"}


async def answer_with_chat(raw_messages: list[Any]) -> dict[str, str]:
    # currently use a singleton AGENT b/c we only have a local usage
    global AGENT
    global RETRIEVER

    if AGENT is None or RETRIEVER is None:
        new_agent()
    try:
        answer = AGENT.run_single_turn(raw_messages[-1])
    except DecisionError:
        # A refused decision is a protocol error, not AGENT output: it carries a
        # status code the transport turns into a failed request.
        raise
    except Exception as e:
        answer = {
            "text": f"Exception happened in chat: {e}. Start a new session to clear the error",
            "reasoning": "",
        }

        AGENT = None
        RETRIEVER = None
    return answer
