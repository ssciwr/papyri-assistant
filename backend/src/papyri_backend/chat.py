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


MODE = "agentic"

agent: LangChainAgent | RetrievalAgent | None = None
RETRIEVER: RetrievalAgent | None = None


async def switch_mode_to(modename: str) -> dict[str, str]:
    if modename not in ["agentic", "basic"]:
        raise ValueError("Error, modename has to be either 'agentic' or 'basic'")
    global MODE
    MODE = modename
    return {"text": f"Switched mode to {modename}", "reasoning": ""}


async def new_agent() -> dict[str, str]:
    global agent
    global RETRIEVER
    try:
        if MODE == "agentic":
            RETRIEVER = make_langchain_retriever(
                os.getenv(
                    "RETRIEVER_CONFIG",
                    str(
                        Path(__file__).resolve().parents[2]
                        / os.getenv(
                            "RETRIEVER_CONFIG", "configs/default_langchain_agent.yaml"
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
        elif MODE == "retrieval":
            agent = make_langchain_retriever(
                os.getenv(
                    "RETRIEVER_CONFIG",
                    str(
                        Path(__file__).resolve().parents[2]
                        / os.getenv(
                            "RETRIEVER_CONFIG", "configs/default_langchain_agent.yaml"
                        )  # TODO: make this env var
                    ),
                )
            )
            return {"text": "RetrieverAgent has been restarted"}
        else:
            raise ValueError(f"Error in  agent creation: Unknown Mode {MODE}")
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
        if MODE in ["agentic", "retrieval"]:
            answer = agent.run_single_turn(raw_messages[-1])
        else:
            raise ValueError(f"Error in  agent communication: Unknown MODE {MODE}")
    except DecisionError:
        # A refused decision is a protocol error, not agent output: it carries a
        # status code the transport turns into a failed request.
        raise
    except Exception as e:
        answer = {"text": f"Exception happened in chat: {e}", "reasoning": ""}

    return answer
