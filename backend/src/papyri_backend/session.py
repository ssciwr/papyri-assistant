"""Own the lifetime of the agent and of the retriever its search tools use."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .langchain_agent import LangChainAgent
from .retrieval import RetrievalAgent

# The backend package root, which the default config paths are relative to.
_ROOT = Path(__file__).resolve().parents[2]

_CURRENT: "Session | None" = None


@dataclass(frozen=True)
class Session:
    """One agent and the retriever backing its search tools."""

    agent: LangChainAgent
    retriever: RetrievalAgent


def _config_path(variable: str, default: str) -> Path:
    """Find a config file, from the environment or from the shipped default.

    Args:
        variable: Name of the environment variable holding the path.
        default: Path to fall back to, relative to the backend directory.

    Returns:
        The path to read the config from.
    """
    # A configured path is used as given, so a relative one stays relative to
    # the working directory the server was started from.
    configured = os.getenv(variable)
    return Path(configured).expanduser() if configured else _ROOT / default


def start() -> Session:
    """Build a new agent and retriever, replacing any current ones.

    Returns:
        The new session.

    Raises:
        RuntimeError: The agent or the retriever could not be built.
    """
    global _CURRENT

    try:
        # The retriever is not an agent of its own: it backs the search tools
        # the agent calls, which is what makes the agentic path into RAG.
        _CURRENT = Session(
            agent=LangChainAgent.from_config(
                _config_path("AGENT_CONFIG", "configs/default_langchain_agent.yaml")
            ),
            retriever=RetrievalAgent.from_config(
                _config_path(
                    "RETRIEVER_CONFIG", "configs/default_langchain_retriever.yaml"
                )
            ),
        )
    except Exception as exc:
        raise RuntimeError(f"Error during agent construction: {exc}") from exc

    return _CURRENT


def current() -> Session:
    """Return the running session, starting one if there is none.

    Returns:
        The current session.
    """
    return _CURRENT if _CURRENT is not None else start()


def clear() -> None:
    """Drop the current session, so the next turn starts a fresh one."""
    global _CURRENT
    _CURRENT = None


def retriever() -> RetrievalAgent:
    """Return the retriever the search tools run against.

    Returns:
        The current session's retriever.
    """
    return current().retriever
