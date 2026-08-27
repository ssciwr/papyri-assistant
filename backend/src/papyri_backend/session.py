"""Own the lifetime of the agent and of the retriever its search tools use."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg

from .langchain_agent import LangChainAgent
from .langchain_retrieval import LangChainRetriever

# The backend package root, which the default config paths are relative to.
_ROOT = Path(__file__).resolve().parents[2]

_CURRENT: "Session | None" = None


@dataclass(frozen=True)
class Session:
    """One agent, the retriever backing its search tools, and their database."""

    agent: LangChainAgent
    retriever: LangChainRetriever
    connection: psycopg.Connection[tuple[Any, ...]]

    def close(self) -> None:
        """Release resources owned by this session."""
        self.connection.close()


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


def _build_connection() -> psycopg.Connection[tuple[Any, ...]]:
    """Connect to the database named by the ``POSTGRES_URL`` environment variable.

    Returns:
        The connection the sql tools run their queries on.

    Raises:
        RuntimeError: ``POSTGRES_URL`` is not set.
    """
    url = os.getenv("POSTGRES_URL")
    if url is None:
        raise RuntimeError("Error, database url env variable not set")
    return psycopg.connect(url)


def start() -> Session:
    """Build a new agent, retriever and database connection, replacing any
    current ones.

    Returns:
        The new session.

    Raises:
        RuntimeError: The agent, the retriever or the connection could not be
            built.
    """
    global _CURRENT

    try:
        # The retriever is not an agent of its own: it backs the search tools
        # the agent calls, which is what makes the agentic path into RAG.
        replacement = Session(
            agent=LangChainAgent.from_config(
                _config_path("AGENT_CONFIG", "configs/default_langchain_agent.yaml")
            ),
            retriever=LangChainRetriever.from_config(
                _config_path(
                    "RETRIEVER_CONFIG", "configs/default_langchain_retriever.yaml"
                )
            ),
            connection=_build_connection(),
        )
    except Exception as exc:
        raise RuntimeError(f"Error during agent construction: {exc}") from exc

    previous = _CURRENT
    _CURRENT = replacement
    if previous is not None:
        previous.close()

    return replacement


def current() -> Session:
    """Return the running session, starting one if there is none.

    Returns:
        The current session.
    """
    return _CURRENT if _CURRENT is not None else start()


def clear() -> None:
    """Close and drop the current session, so the next turn starts a fresh one."""
    global _CURRENT

    current = _CURRENT
    _CURRENT = None
    if current is not None:
        current.close()


def retriever() -> LangChainRetriever:
    """Return the retriever the search tools run against.

    Returns:
        The current session's retriever.
    """
    return current().retriever


def connection() -> psycopg.Connection[tuple[Any, ...]]:
    """Return the connection the sql tools run their queries on.

    Returns:
        The current session's database connection.
    """
    return current().connection
