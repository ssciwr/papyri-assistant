"""Cover the FastAPI layer's established units and public route contracts.

The agent is replaced by a fake, so both the direct handler baselines and the
TestClient route tests run without reaching a model.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest
from fastapi import Response
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import ValidationError

from papyri_backend import server
from papyri_backend.exceptions import InvalidDecision, StaleDecision


def test_app_is_named() -> None:
    # The title is what the generated OpenAPI docs are published under.
    assert server.app.title == "Papyri Backend"


def test_app_lifespan_starts_and_clears_the_session(monkeypatch) -> None:
    events: list[str] = []
    monkeypatch.setattr(server.session, "start", lambda: events.append("start"))
    monkeypatch.setattr(server.session, "clear", lambda: events.append("clear"))

    with TestClient(server.app):
        assert events == ["start"]

    assert events == ["start", "clear"]


def test_cors_origins_splits_and_strips_env(monkeypatch) -> None:
    # A hand-written list tends to carry stray spaces and a trailing comma; an
    # origin that keeps its whitespace never matches the browser's Origin
    # header, and an empty one would allow nothing under a plausible-looking
    # config.
    monkeypatch.setenv("CORS_ORIGIN", " http://localhost:5173, ,https://example.test ")

    assert server._cors_origins() == ["http://localhost:5173", "https://example.test"]


def test_cors_origins_uses_frontend_default(monkeypatch) -> None:
    # With nothing configured the dev frontend still has to be able to call the
    # backend, so the vite dev server's origin is the default.
    monkeypatch.delenv("CORS_ORIGIN", raising=False)

    assert server._cors_origins() == ["http://localhost:5173"]


def test_chat_request_requires_at_least_one_message() -> None:
    # An empty conversation has no question in it. Rejecting it in the model
    # means the endpoint never has to handle that case.
    with pytest.raises(ValidationError):
        server.ChatRequest(messages=[])


def test_health_returns_ok() -> None:
    # The liveness probe: it must answer without touching the agent.
    assert asyncio.run(server.health()) == {"ok": True}


def test_prepare_chat_returns_events_and_streaming_headers(monkeypatch) -> None:
    # The fake stands in for the agent and asserts what it was handed, which is
    # how the test pins that the endpoint forwards the messages unchanged.
    def fake_answer_with_chat_stream(messages: list[object]):
        assert messages == [{"role": "user", "content": "Hi"}]
        return iter(
            [
                {"type": "text", "content": "Hello"},
                {"type": "done", "interrupt": None},
            ]
        )

    monkeypatch.setattr(server, "answer_with_chat_stream", fake_answer_with_chat_stream)

    response = Response()
    events = server._prepare_chat(
        server.ChatRequest(messages=[{"role": "user", "content": "Hi"}]), response
    )

    assert list(events) == [
        {"type": "text", "content": "Hello"},
        {"type": "done", "interrupt": None},
    ]
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["x-accel-buffering"] == "no"


def test_chat_route_is_documented_as_typed_json_lines() -> None:
    content = server.app.openapi()["paths"]["/chat"]["post"]["responses"]["200"][
        "content"
    ]

    assert content == {
        "application/jsonl": {
            "itemSchema": {"$ref": "#/components/schemas/ChatStreamEvent"}
        }
    }


def test_validation_exception_handler_returns_client_error() -> None:
    # The handler ignores both of its arguments, so an empty error and no
    # request are enough to exercise it.
    response = asyncio.run(
        server.validation_exception_handler(None, RequestValidationError([]))
    )

    # A malformed body is the client's mistake, so it is a 400 with a message
    # saying what was expected, rather than FastAPI's default 422 field dump.
    assert response.status_code == 400
    assert json.loads(response.body) == {
        "error": "Expected a JSON body with a messages array."
    }


@pytest.fixture
def client() -> TestClient:
    return TestClient(server.app)


def test_health_route(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_new_route(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(
        server, "new_agent", lambda: {"text": "DeepAgent has been restarted"}
    )

    response = client.post("/new")

    assert response.status_code == 200
    assert response.json() == {
        "text": "DeepAgent has been restarted",
        "reasoning": "",
        "interrupt": None,
    }


def test_new_route_reports_agent_errors(client: TestClient, monkeypatch) -> None:
    def fail_to_start() -> dict[str, str]:
        raise RuntimeError("startup failed")

    monkeypatch.setattr(server, "new_agent", fail_to_start)

    response = client.post("/new")

    assert response.status_code == 500
    assert response.json() == {"error": "startup failed"}


def test_chat_route(client: TestClient, monkeypatch) -> None:
    def answer(messages: list[Any]):
        assert messages == [{"role": "user", "content": "Hi"}]
        return iter(
            [
                {"type": "reasoning", "content": "Thinking"},
                {"type": "text", "content": "Hello"},
                {"type": "done", "interrupt": None},
            ]
        )

    monkeypatch.setattr(server, "answer_with_chat_stream", answer)

    response = client.post(
        "/chat", json={"messages": [{"role": "user", "content": "Hi"}]}
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/jsonl")
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["x-accel-buffering"] == "no"
    assert [json.loads(line) for line in response.text.splitlines()] == [
        {"type": "reasoning", "content": "Thinking", "interrupt": None},
        {"type": "text", "content": "Hello", "interrupt": None},
        {"type": "done", "content": "", "interrupt": None},
    ]


@pytest.mark.parametrize(
    ("error", "status_code"),
    [
        (StaleDecision("decision is stale"), 409),
        (InvalidDecision("decision is invalid"), 422),
    ],
)
def test_chat_route_preserves_decision_error_status(
    client: TestClient, monkeypatch, error: Exception, status_code: int
) -> None:
    def refuse(_messages: list[Any]):
        raise error

    monkeypatch.setattr(server, "answer_with_chat_stream", refuse)

    response = client.post("/chat", json={"messages": [{"content": "decision"}]})

    assert response.status_code == status_code
    assert response.json() == {"error": str(error)}


@pytest.mark.parametrize("body", [None, {}, {"messages": []}])
def test_chat_route_rejects_invalid_requests(client: TestClient, body: Any) -> None:
    response = client.post("/chat", json=body)

    assert response.status_code == 400
    assert response.json() == {"error": "Expected a JSON body with a messages array."}
