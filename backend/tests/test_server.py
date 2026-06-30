from __future__ import annotations

import asyncio
import json

import pytest
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from papyri_backend import server


def test_app_is_named() -> None:
    assert server.app.title == "Papyri Backend"


def test_cors_origins_splits_and_strips_env(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ORIGIN", " http://localhost:5173, ,https://example.test ")

    assert server._cors_origins() == ["http://localhost:5173", "https://example.test"]


def test_cors_origins_uses_frontend_default(monkeypatch) -> None:
    monkeypatch.delenv("CORS_ORIGIN", raising=False)

    assert server._cors_origins() == ["http://localhost:5173"]


def test_chat_request_requires_at_least_one_message() -> None:
    with pytest.raises(ValidationError):
        server.ChatRequest(messages=[])


def test_health_returns_ok() -> None:
    assert asyncio.run(server.health()) == {"ok": True}


def test_chat_returns_answer(monkeypatch) -> None:
    async def fake_answer_with_chat(messages: list[object]) -> dict[str, str]:
        assert messages == [{"role": "user", "content": "Hi"}]
        return {"text": "Hello"}

    monkeypatch.setattr(server, "answer_with_chat", fake_answer_with_chat)

    response = asyncio.run(
        server.chat(server.ChatRequest(messages=[{"role": "user", "content": "Hi"}]))
    )

    assert response == {"text": "Hello"}


def test_chat_returns_json_response_on_error(monkeypatch) -> None:
    async def fake_answer_with_chat(_messages: list[object]) -> dict[str, str]:
        raise RuntimeError("provider failed")

    monkeypatch.setattr(server, "answer_with_chat", fake_answer_with_chat)

    response = asyncio.run(
        server.chat(server.ChatRequest(messages=[{"role": "user", "content": "Hi"}]))
    )

    assert response.status_code == 500
    assert json.loads(response.body) == {"error": "provider failed"}


def test_validation_exception_handler_returns_client_error() -> None:
    response = asyncio.run(
        server.validation_exception_handler(None, RequestValidationError([]))
    )

    assert response.status_code == 400
    assert json.loads(response.body) == {
        "error": "Expected a JSON body with a messages array."
    }
