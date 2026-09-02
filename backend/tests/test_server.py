"""Cover the FastAPI layer's established units and public route contracts.

The agent is replaced by a fake, so both the direct handler baselines and the
TestClient route tests run without reaching a model.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest
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


def test_chat_returns_answer(monkeypatch) -> None:
    # The fake stands in for the agent and asserts what it was handed, which is
    # how the test pins that the endpoint forwards the messages unchanged.
    def fake_answer_with_chat_stream(messages: list[object]):
        assert messages == [{"role": "user", "content": "Hi"}]
        return iter(
            [
                {
                    "text": "Hello",
                    "reasoning": "",
                    "interrupt": None,
                    "done": True,
                }
            ]
        )

    monkeypatch.setattr(server, "answer_with_chat_stream", fake_answer_with_chat_stream)

    # asyncio.run drives the coroutine, since the endpoint is called directly
    # rather than through a test client.
    response = asyncio.run(
        server.chat(server.ChatRequest(messages=[{"role": "user", "content": "Hi"}]))
    )

    assert response.media_type == "application/x-ndjson"
    assert response.headers["x-accel-buffering"] == "no"


def test_chat_returns_json_response_on_error(monkeypatch) -> None:
    def fake_answer_with_chat_stream(_messages: list[object]):
        raise RuntimeError("provider failed")

    monkeypatch.setattr(server, "answer_with_chat_stream", fake_answer_with_chat_stream)

    response = asyncio.run(
        server.chat(server.ChatRequest(messages=[{"role": "user", "content": "Hi"}]))
    )

    # A failing agent must not escape as an unhandled exception: the client gets
    # a 500 carrying the reason. Note that this deliberately forwards the
    # provider's own message, which suits local development.
    assert response.status_code == 500
    assert json.loads(response.body) == {"error": "provider failed"}


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
                {
                    "text": "",
                    "reasoning": "Thinking",
                    "interrupt": None,
                    "done": False,
                },
                {
                    "text": "Hello",
                    "reasoning": "Thinking",
                    "interrupt": None,
                    "done": True,
                },
            ]
        )

    monkeypatch.setattr(server, "answer_with_chat_stream", answer)

    response = client.post(
        "/chat", json={"messages": [{"role": "user", "content": "Hi"}]}
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")
    assert [json.loads(line) for line in response.text.splitlines()] == [
        {
            "text": "",
            "reasoning": "Thinking",
            "interrupt": None,
            "done": False,
        },
        {
            "text": "Hello",
            "reasoning": "Thinking",
            "interrupt": None,
            "done": True,
        },
    ]


def test_chat_route_reports_agent_errors(client: TestClient, monkeypatch) -> None:
    def fail(_messages: list[Any]):
        raise RuntimeError("provider failed")

    monkeypatch.setattr(server, "answer_with_chat_stream", fail)

    response = client.post("/chat", json={"messages": [{"content": "Hi"}]})

    assert response.status_code == 500
    assert response.json() == {"error": "provider failed"}


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
