"""Unit tests for atomic session construction and resource ownership."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

from papyri_backend import session


class ClosingResource:
    def __init__(self) -> None:
        self.close_calls = 0

    def close(self) -> None:
        self.close_calls += 1


def _session(
    connection: ClosingResource | None = None, engine: ClosingResource | None = None
) -> session.Session:
    return session.Session(
        agent=cast(Any, object()),
        retrievers=cast(Any, {"transcriptions": object()}),
        connection=cast(Any, connection or ClosingResource()),
        vector_engine=cast(Any, engine or ClosingResource()),
    )


def test_config_path_uses_default_and_expands_configured_home(monkeypatch, tmp_path):
    monkeypatch.delenv("AGENT_CONFIG", raising=False)
    assert session._config_path("AGENT_CONFIG", "configs/agent.yaml") == (
        session._ROOT / "configs/agent.yaml"
    )
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AGENT_CONFIG", "~/.config/papyri/agent.yaml")
    assert session._config_path("AGENT_CONFIG", "ignored") == (
        tmp_path / ".config/papyri/agent.yaml"
    )
    monkeypatch.setenv("AGENT_CONFIG", "relative.yaml")
    assert session._config_path("AGENT_CONFIG", "ignored") == Path("relative.yaml")


def test_build_connection_requires_and_uses_database_url(monkeypatch):
    monkeypatch.delenv("POSTGRES_URL", raising=False)
    with pytest.raises(RuntimeError, match="database url"):
        session._build_connection()
    connected: list[str] = []
    monkeypatch.setenv("POSTGRES_URL", "postgresql://reader@db/papyri")
    monkeypatch.setattr(
        session.psycopg, "connect", lambda url: connected.append(url) or object()
    )
    session._build_connection()
    assert connected == ["postgresql://reader@db/papyri"]


def test_start_publishes_complete_replacement_then_closes_previous(monkeypatch):
    previous_connection = ClosingResource()
    previous_engine = ClosingResource()
    previous = _session(previous_connection, previous_engine)
    connection = ClosingResource()
    engine = ClosingResource()
    agent = object()
    retrievers = {"transcriptions": object()}
    monkeypatch.setattr(session, "_CURRENT", previous)
    monkeypatch.setattr(session.LangChainAgent, "from_config", lambda _path: agent)
    monkeypatch.setattr(session, "_build_connection", lambda: connection)
    monkeypatch.setattr(
        session, "build_retrievers", lambda value: (retrievers, engine)
    )

    result = session.start()

    assert result.agent is agent
    assert result.retrievers is retrievers
    assert result.connection is connection
    assert result.vector_engine is engine
    assert session._CURRENT is result
    assert previous_connection.close_calls == 1
    assert previous_engine.close_calls == 1


def test_start_closes_partial_resources_and_keeps_previous(monkeypatch):
    previous = _session()
    connection = ClosingResource()
    cause = ValueError("bad embedding metadata")
    monkeypatch.setattr(session, "_CURRENT", previous)
    monkeypatch.setattr(session.LangChainAgent, "from_config", lambda _path: object())
    monkeypatch.setattr(session, "_build_connection", lambda: connection)
    monkeypatch.setattr(
        session,
        "build_retrievers",
        lambda _connection: (_ for _ in ()).throw(cause),
    )

    with pytest.raises(RuntimeError, match="agent construction") as raised:
        session.start()

    assert raised.value.__cause__ is cause
    assert connection.close_calls == 1
    assert session._CURRENT is previous


def test_current_clear_and_accessors(monkeypatch):
    connection = ClosingResource()
    engine = ClosingResource()
    value = _session(connection, engine)
    monkeypatch.setattr(session, "_CURRENT", value)
    assert session.current() is value
    assert session.connection() is connection
    assert session.retriever("transcriptions") is value.retrievers["transcriptions"]
    with pytest.raises(ValueError, match="Unknown embedding corpus"):
        session.retriever(cast(Any, "other"))
    session.clear()
    assert session._CURRENT is None
    assert connection.close_calls == 1
    assert engine.close_calls == 1


def test_current_starts_only_when_empty(monkeypatch):
    created = _session()
    monkeypatch.setattr(session, "_CURRENT", None)
    monkeypatch.setattr(session, "start", lambda: created)
    assert session.current() is created
