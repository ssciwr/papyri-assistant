"""The chat model adapter, with no network.

What matters is the asymmetry: the reasoning trace must reach the caller and
must not reach the model again.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from langchain_core.messages import AIMessage, AIMessageChunk
from langchain_openai.chat_models.base import _convert_message_to_dict

from papyri_backend.chat_models import MaybeVLLMChatOpenAI


@pytest.fixture
def unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    """No endpoint answers, which is the normal case in the test suite."""

    def refuse(*args: Any, **kwargs: Any) -> httpx.Response:
        raise httpx.ConnectError("no endpoint here")

    monkeypatch.setattr(httpx, "get", refuse)


def model() -> MaybeVLLMChatOpenAI:
    return MaybeVLLMChatOpenAI(
        model="a-reasoning-model", base_url="http://nowhere/v1", api_key="unused"
    )


def chunk(**delta: Any) -> dict[str, Any]:
    return {"choices": [{"delta": delta, "index": 0}]}


def test_an_endpoint_that_cannot_be_reached_still_builds(unreachable: None) -> None:
    # The agent is built during startup, so a model that is down must not stop
    # the server from coming up.
    assert model()._is_vllm is False


@pytest.mark.parametrize("field", ["reasoning", "reasoning_content"])
def test_either_spelling_of_the_trace_is_preserved(
    unreachable: None, field: str
) -> None:
    generation = model()._convert_chunk_to_generation_chunk(
        chunk(**{field: "weighing the evidence"}), AIMessageChunk, None
    )

    assert generation is not None
    message = generation.message
    # langchain_core only builds the block when the provider is not "openai".
    assert message.response_metadata["model_provider"] == "vllm"
    assert message.content_blocks == [
        {"type": "reasoning", "reasoning": "weighing the evidence"}
    ]
    assert message.text == ""


def test_a_chunk_without_a_trace_is_left_alone(unreachable: None) -> None:
    generation = model()._convert_chunk_to_generation_chunk(
        chunk(content="the answer"), AIMessageChunk, None
    )

    assert generation is not None
    assert generation.message.text == "the answer"
    assert "reasoning_content" not in generation.message.additional_kwargs


def test_the_trace_is_not_sent_back_to_the_model() -> None:
    """The reason the trace lives in additional_kwargs rather than content.

    Silent when it breaks: the answer is still right and the verdict is still
    read, while the model is quietly fed its own earlier reasoning.
    """
    message = AIMessage(
        content="the answer", additional_kwargs={"reasoning_content": "a long trace"}
    )

    assert "a long trace" not in str(_convert_message_to_dict(message))
