"""Own the lifetime of the agent and of the retriever its search tools use."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg

from .langchain_agent import LangChainAgent
from .langchain_retrieval import (
    Corpus,
    LangChainRetriever,
    PGEngine,
    build_retrievers,
    close_vector_engine,
)

# The backend package root, which the default config paths are relative to.
_ROOT = Path(__file__).resolve().parents[2]

_CURRENT: "Session | None" = None


@dataclass(frozen=True)
class Session:
    """One agent, three corpus retrievers, and their owned database resources."""

    agent: LangChainAgent
    retrievers: dict[Corpus, LangChainRetriever]
    connection: psycopg.Connection[tuple[Any, ...]]
    vector_engine: PGEngine

    def close(self) -> None:
        """Release resources owned by this session."""
        try:
            close_vector_engine(self.vector_engine)
        finally:
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

    connection: psycopg.Connection[tuple[Any, ...]] | None = None
    vector_engine: PGEngine | None = None
    try:
        # The retriever is not an agent of its own: it backs the search tools
        # the agent calls, which is what makes the agentic path into RAG.
        agent = LangChainAgent.from_config(
            _config_path("AGENT_CONFIG", "configs/default_langchain_agent.yaml")
        )

        connection = _build_connection()
        retrievers, vector_engine = build_retrievers(connection)

        replacement = Session(
            agent=agent,
            retrievers=retrievers,
            connection=connection,
            vector_engine=vector_engine,
        )
    except Exception as exc:
        if vector_engine is not None:
            close_vector_engine(vector_engine)
        if connection is not None:
            connection.close()
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


def retriever(corpus: Corpus) -> LangChainRetriever:
    """Return the requested corpus retriever used by the search tools.

    Returns:
        The current session's retriever.
    """
    try:
        return current().retrievers[corpus]
    except KeyError as error:
        choices = ", ".join(current().retrievers)
        raise ValueError(
            f"Unknown embedding corpus {corpus!r}. Expected one of: {choices}"
        ) from error


def connection() -> psycopg.Connection[tuple[Any, ...]]:
    """Return the connection the sql tools run their queries on.

    Returns:
        The current session's database connection.
    """
    return current().connection
