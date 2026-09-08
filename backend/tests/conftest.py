"""Deterministic fakes and papyrological fixtures shared by backend tests."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

import pytest


@dataclass
class FakeToolCalls:
    """Expose model tool calls through the interface the agent adapter reads."""

    calls: list[dict[str, Any]] = field(default_factory=list)

    def get(self) -> list[dict[str, Any]]:
        return self.calls


@dataclass
class FakeStreamMessage:
    """One message emitted by the fake v3 graph event stream."""

    text: str = ""
    reasoning: str = ""
    tool_calls: FakeToolCalls = field(default_factory=FakeToolCalls)


@dataclass
class FakeStreamRun:
    """A drained graph run with the messages it emitted."""

    messages: Iterable[FakeStreamMessage] = field(default_factory=list)


@dataclass
class FakeInterrupt:
    """The minimal interrupt shape retained by the LangGraph checkpointer."""

    id: str = "interrupt-lease-review"
    value: dict[str, Any] = field(
        default_factory=lambda: {
            "action_requests": [
                {
                    "name": "write_file",
                    "args": {"file_path": "/app/workspace/lease-notes.md"},
                }
            ],
            "review_configs": [
                {"allowed_decisions": ["approve", "edit", "reject", "respond"]}
            ],
        }
    )


@dataclass
class FakeGraphState:
    """Graph state as observed through ``get_state``."""

    interrupts: list[FakeInterrupt] = field(default_factory=list)


class FakeGraph:
    """A checkpointer-facing graph fake with deterministic stream behaviour."""

    def __init__(
        self,
        messages: Iterable[FakeStreamMessage] = (),
        *,
        interrupts: Iterable[FakeInterrupt] = (),
        tool_names: Iterable[str] = (),
        error: Exception | None = None,
        error_after_messages: Exception | None = None,
    ) -> None:
        self.messages = list(messages)
        self.error = error
        self.error_after_messages = error_after_messages
        self.calls: list[dict[str, Any]] = []
        self.states: dict[str, FakeGraphState] = {
            "default": FakeGraphState(list(interrupts))
        }
        self.nodes = {
            "tools": SimpleNamespace(
                bound=SimpleNamespace(
                    tools_by_name={name: object() for name in tool_names}
                )
            )
        }

    def stream_events(
        self, payload: Any, *, config: Mapping[str, Any], version: str
    ) -> FakeStreamRun:
        self.calls.append({"payload": payload, "config": config, "version": version})
        if self.error is not None:
            raise self.error
        if hasattr(payload, "resume"):
            # A successfully accepted decision consumes the checkpoint pause.
            for state in self.states.values():
                state.interrupts.clear()

        def messages() -> Iterable[FakeStreamMessage]:
            yield from self.messages
            if self.error_after_messages is not None:
                raise self.error_after_messages

        return FakeStreamRun(messages())

    def get_state(self, config: Mapping[str, Any]) -> FakeGraphState:
        thread_id = config.get("configurable", {}).get("thread_id", "default")
        return self.states.get(thread_id, self.states["default"])


class FakeCursor:
    """A psycopg cursor/result that records fetches and can fail deterministically."""

    def __init__(
        self, rows: Iterable[tuple[Any, ...]] = (), *, error: Exception | None = None
    ):
        self.rows = list(rows)
        self.error = error
        self.fetchall_calls = 0

    def fetchall(self) -> list[tuple[Any, ...]]:
        self.fetchall_calls += 1
        if self.error is not None:
            raise self.error
        return self.rows


class FakeConnection:
    """A psycopg connection fake used by read-only SQL tool tests."""

    def __init__(
        self,
        rows: Iterable[tuple[Any, ...]] = (),
        *,
        execute_error: Exception | None = None,
        fetch_error: Exception | None = None,
    ) -> None:
        self.queries: list[str] = []
        self.rollback_calls = 0
        self.execute_error = execute_error
        self.cursor = FakeCursor(rows, error=fetch_error)

    def execute(self, query: str) -> FakeCursor:
        self.queries.append(query)
        if self.execute_error is not None:
            raise self.execute_error
        return self.cursor

    def rollback(self) -> None:
        self.rollback_calls += 1


class FakeRetriever:
    """A vector-search facade that records every adapter call."""

    def __init__(
        self,
        documents: Iterable[Any] = (),
        *,
        error: Exception | None = None,
    ) -> None:
        self.documents = list(documents)
        self.error = error
        self.calls: list[tuple[str, Any]] = []

    def _search(self, method: str, query: Any) -> list[Any]:
        self.calls.append((method, query))
        if self.error is not None:
            raise self.error
        return self.documents

    def similarity_search(self, query: str) -> list[Any]:
        return self._search("similarity_search", query)

    def mmr_search(self, query: str) -> list[Any]:
        return self._search("mmr_search", query)

    def similarity_search_by_vec(self, vector: list[float]) -> list[Any]:
        return self._search("similarity_search_by_vec", vector)

    def mmr_search_by_vec(self, vector: list[float]) -> list[Any]:
        return self._search("mmr_search_by_vec", vector)


@pytest.fixture
def papyrus_record() -> dict[str, Any]:
    """A realistic synthetic Oxyrhynchus lease record safe to commit to tests."""
    return {
        "tm_id": 123456,
        "transcription_id": 789,
        "source_path": "P.Oxy./P.Oxy.12.1450.xml",
        "document_type": "lease",
        "provenance": "Oxyrhynchus, Egypt",
        "language": "grc",
        "date_range": {"not_before_year": 100, "not_after_year": 125},
        "transcription": "μίσθωσις οἰκίας παρὰ Διδύμῃ",
        "translation": "Lease of a house from Didyme.",
        "citation": "P.Oxy. XII 1450",
        "source": "synthetic-fixture",
        "dates": [
            {
                "text": "100–125 CE",
                "not_before_year": 100,
                "not_after_year": 125,
                "alternative": False,
            }
        ],
        "places": [
            {
                "name": "Oxyrhynchus",
                "full_name": "Oxyrhynchus, Egypt",
                "type": "ancient city",
                "granularity": "city",
                "tm_place_id": 1234,
                "pleiades_place_id": 756638,
            }
        ],
    }


@pytest.fixture
def user_message() -> Callable[[str], dict[str, Any]]:
    """Build an ordinary user message in the backend's current content shape."""
    return lambda text: {
        "role": "user",
        "content": [{"type": "text", "text": text}],
    }


@pytest.fixture
def decision_reply(
    user_message: Callable[[str], dict[str, Any]],
) -> Callable[[str, list[dict[str, Any]] | None], dict[str, Any]]:
    """Build a JSON decision reply wrapped as an ordinary user message."""

    def build(
        interrupt_id: str, decisions: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        return user_message(
            json.dumps(
                {
                    "interrupt_id": interrupt_id,
                    "decisions": decisions or [{"type": "approve"}],
                }
            )
        )

    return build


@pytest.fixture
def fake_graph() -> FakeGraph:
    return FakeGraph()


@pytest.fixture
def fake_interrupt() -> FakeInterrupt:
    return FakeInterrupt()


@pytest.fixture
def fake_connection() -> FakeConnection:
    return FakeConnection()


@pytest.fixture
def fake_retriever(papyrus_record: Mapping[str, Any]) -> FakeRetriever:
    return FakeRetriever([papyrus_record])
