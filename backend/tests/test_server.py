"""Cover the FastAPI layer: its configuration, its request model and its handlers.

The endpoint functions are called directly, and the agent behind them is
replaced by a fake, so these tests exercise the HTTP layer's own behaviour
without starting a server or reaching a model.
"""

from __future__ import annotations

import asyncio
import json

import pytest
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from papyri_backend import server


def test_app_is_named() -> None:
    # The title is what the generated OpenAPI docs are published under.
    assert server.app.title == "Papyri Backend"


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
    async def fake_answer_with_chat(messages: list[object]) -> dict[str, str]:
        assert messages == [{"role": "user", "content": "Hi"}]
        return {"text": "Hello"}

    monkeypatch.setattr(server, "answer_with_chat", fake_answer_with_chat)

    # asyncio.run drives the coroutine, since the endpoint is called directly
    # rather than through a test client.
    response = asyncio.run(
        server.chat(server.ChatRequest(messages=[{"role": "user", "content": "Hi"}]))
    )

    # On the happy path the answer is returned as a plain dict, which FastAPI
    # then validates against ChatResponse.
    assert response == {"text": "Hello"}


def test_chat_returns_json_response_on_error(monkeypatch) -> None:
    async def fake_answer_with_chat(_messages: list[object]) -> dict[str, str]:
        raise RuntimeError("provider failed")

    monkeypatch.setattr(server, "answer_with_chat", fake_answer_with_chat)

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
