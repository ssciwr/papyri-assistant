"""Tests for chat model provider adaptations."""

from types import SimpleNamespace

from langchain_core.messages import AIMessageChunk

from papyri_backend import chat_models
from papyri_backend.chat_models import MaybeVLLMChatOpenAI


def test_vllm_streaming_reasoning_is_preserved(monkeypatch) -> None:
    request = {}

    def get(url, **kwargs):
        request.update(url=url, **kwargs)
        return SimpleNamespace(status_code=200, json=lambda: {"version": "0.28.0"})

    monkeypatch.setattr(chat_models.httpx, "get", get)
    model = MaybeVLLMChatOpenAI(
        model="test-model",
        base_url="http://localhost:9999/v1",
        api_key="test-key",
    )

    generation = model._convert_chunk_to_generation_chunk(
        {"choices": [{"delta": {"reasoning": "Plan"}, "finish_reason": None}]},
        AIMessageChunk,
        None,
    )

    assert request == {
        "url": "http://localhost:9999/version",
        "headers": {"Authorization": "Bearer test-key"},
        "timeout": 5.0,
    }
    assert generation is not None
    assert generation.message.additional_kwargs == {"reasoning_content": "Plan"}
    assert generation.message.response_metadata["model_provider"] == "vllm"
    assert generation.message.content_blocks == [
        {"type": "reasoning", "reasoning": "Plan"}
    ]
