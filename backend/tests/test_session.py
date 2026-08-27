"""Unit tests for ownership and lifecycle of the backend chat session."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

from papyri_backend import session


class ClosingConnection:
    def __init__(self) -> None:
        self.close_calls = 0

    def close(self) -> None:
        self.close_calls += 1


def _session(connection: object | None = None) -> session.Session:
    return session.Session(
        agent=cast(Any, object()),
        retriever=cast(Any, object()),
        connection=cast(
            Any, connection if connection is not None else ClosingConnection()
        ),
    )


def test_config_path_uses_the_shipped_default_when_unconfigured(monkeypatch) -> None:
    monkeypatch.delenv("AGENT_CONFIG", raising=False)

    assert session._config_path("AGENT_CONFIG", "configs/agent.yaml") == (
        session._ROOT / "configs/agent.yaml"
    )


def test_config_path_expands_home_but_preserves_relative_paths(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AGENT_CONFIG", "~/.config/papyri/agent.yaml")
    monkeypatch.setenv("RETRIEVER_CONFIG", "configs/alternate-retriever.yaml")

    assert session._config_path("AGENT_CONFIG", "ignored.yaml") == (
        tmp_path / ".config/papyri/agent.yaml"
    )
    assert session._config_path("RETRIEVER_CONFIG", "ignored.yaml") == Path(
        "configs/alternate-retriever.yaml"
    )


def test_build_connection_requires_a_database_url(monkeypatch) -> None:
    monkeypatch.delenv("POSTGRES_URL", raising=False)

    with pytest.raises(RuntimeError, match="database url env variable not set"):
        session._build_connection()


def test_build_connection_uses_the_configured_database_url(monkeypatch) -> None:
    connected_to: list[str] = []
    connection = object()
    monkeypatch.setenv("POSTGRES_URL", "postgresql://papyri:test@db/papyri")
    monkeypatch.setattr(
        session.psycopg,
        "connect",
        lambda url: connected_to.append(url) or connection,
    )

    assert session._build_connection() is connection
    assert connected_to == ["postgresql://papyri:test@db/papyri"]


def test_start_constructs_and_publishes_a_complete_session(monkeypatch) -> None:
    agent = object()
    retriever = object()
    connection = object()
    constructed_from: list[tuple[str, Path]] = []
    previous = _session()
    monkeypatch.setattr(session, "_CURRENT", previous)
    monkeypatch.delenv("AGENT_CONFIG", raising=False)
    monkeypatch.delenv("RETRIEVER_CONFIG", raising=False)
    monkeypatch.setattr(
        session.LangChainAgent,
        "from_config",
        lambda path: constructed_from.append(("agent", path)) or agent,
    )
    monkeypatch.setattr(
        session.LangChainRetriever,
        "from_config",
        lambda path: constructed_from.append(("retriever", path)) or retriever,
    )
    monkeypatch.setattr(session, "_build_connection", lambda: connection)

    result = session.start()

    assert result == session.Session(
        agent=cast(Any, agent),
        retriever=cast(Any, retriever),
        connection=cast(Any, connection),
    )
    assert session._CURRENT is result
    assert result is not previous
    assert constructed_from == [
        ("agent", session._ROOT / "configs/default_langchain_agent.yaml"),
        ("retriever", session._ROOT / "configs/default_langchain_retriever.yaml"),
    ]


def test_start_closes_the_connection_of_the_replaced_session(monkeypatch) -> None:
    previous_connection = ClosingConnection()
    previous = _session(previous_connection)
    new_connection = ClosingConnection()
    monkeypatch.setattr(session, "_CURRENT", previous)
    monkeypatch.setattr(session.LangChainAgent, "from_config", lambda _path: object())
    monkeypatch.setattr(
        session.LangChainRetriever, "from_config", lambda _path: object()
    )
    monkeypatch.setattr(session, "_build_connection", lambda: new_connection)

    current = session.start()

    assert current is session._CURRENT
    assert current is not previous
    assert previous_connection.close_calls == 1
    assert new_connection.close_calls == 0


def test_start_wraps_construction_errors_without_replacing_the_current_session(
    monkeypatch,
) -> None:
    previous_connection = ClosingConnection()
    previous = _session(previous_connection)
    cause = ValueError("invalid agent config")
    monkeypatch.setattr(session, "_CURRENT", previous)
    monkeypatch.setattr(
        session.LangChainAgent,
        "from_config",
        lambda _path: (_ for _ in ()).throw(cause),
    )

    with pytest.raises(
        RuntimeError, match="Error during agent construction"
    ) as excinfo:
        session.start()

    assert excinfo.value.__cause__ is cause
    assert session._CURRENT is previous
    assert previous_connection.close_calls == 0


def test_current_starts_once_then_reuses_the_same_session(monkeypatch) -> None:
    created = _session()
    starts = 0
    monkeypatch.setattr(session, "_CURRENT", None)

    def start() -> session.Session:
        nonlocal starts
        starts += 1
        monkeypatch.setattr(session, "_CURRENT", created)
        return created

    monkeypatch.setattr(session, "start", start)

    assert session.current() is created
    assert session.current() is created
    assert starts == 1


def test_clear_drops_the_current_session_and_closes_its_connection(monkeypatch) -> None:
    connection = ClosingConnection()
    monkeypatch.setattr(session, "_CURRENT", _session(connection))

    session.clear()
    session.clear()

    assert session._CURRENT is None
    assert connection.close_calls == 1


def test_retriever_and_connection_delegate_to_the_current_session(monkeypatch) -> None:
    current = _session()
    monkeypatch.setattr(session, "_CURRENT", current)

    assert session.retriever() is current.retriever
    assert session.connection() is current.connection
