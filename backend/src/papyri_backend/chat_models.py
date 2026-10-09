"""Chat model adapters used by the Papyri assistant."""

from typing import Any

import httpx
from langchain_core.messages import AIMessageChunk
from langchain_core.outputs import ChatGenerationChunk
from langchain_openai import ChatOpenAI
from pydantic import PrivateAttr

# Gateways disagree on the name: vLLM sends "reasoning", LiteLLM sends
# "reasoning_content".
_REASONING_FIELDS = ("reasoning", "reasoning_content")


def _reasoning_delta(chunk: dict) -> str:
    """Return this chunk's reasoning text, or "" when it carries none."""
    choices = chunk.get("choices") or chunk.get("chunk", {}).get("choices") or []
    delta = choices[0].get("delta") if choices else None
    for field in _REASONING_FIELDS:
        reasoning = (delta or {}).get(field)
        if reasoning:
            return str(reasoning)
    return ""


class MaybeVLLMChatOpenAI(ChatOpenAI):
    """Preserve reasoning chunks when an OpenAI-compatible endpoint sends them.

    ``ChatOpenAI`` stamps ``model_provider`` as "openai", and langchain_core
    then ignores ``additional_kwargs["reasoning_content"]`` when it builds
    content blocks. Naming a different provider restores the trace, which
    reaches the caller as a reasoning block while staying out of the message
    content - so it is never sent back to the model. Feeding a reasoning model
    its own earlier trace is a known way to provoke a repetition loop.
    """

    _is_vllm: bool = PrivateAttr(default=False)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._is_vllm = self._endpoint_is_vllm()

    def _endpoint_is_vllm(self) -> bool:
        """Ask the endpoint whether it is vLLM, tolerating no answer.

        An unreachable endpoint means "not known to be vLLM" rather than a
        failure to construct: the agent is built during application startup,
        and a model that happens to be down should not stop the server coming
        up. A gateway that answers nothing is handled by reading the reasoning
        field itself, below.
        """
        base_url = str(self.root_client.base_url).rstrip("/").removesuffix("/v1")
        api_key = self.openai_api_key.get_secret_value()
        try:
            response = httpx.get(
                f"{base_url}/version",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=5.0,
            )
            return response.status_code == 200 and "version" in response.json()
        except Exception:
            return False

    def _convert_chunk_to_generation_chunk(
        self,
        chunk: dict,
        default_chunk_class: type,
        base_generation_info: dict | None,
    ) -> ChatGenerationChunk | None:
        generation_chunk = super()._convert_chunk_to_generation_chunk(
            chunk, default_chunk_class, base_generation_info
        )
        if generation_chunk is None:
            return generation_chunk

        reasoning = _reasoning_delta(chunk)
        # A reasoning field is itself sufficient evidence to preserve: LiteLLM
        # serves vLLM models without answering /version, so waiting for the
        # probe would discard the trace on every gateway but vLLM itself.
        if not (self._is_vllm or reasoning):
            return generation_chunk

        generation_chunk.message.response_metadata["model_provider"] = "vllm"
        if reasoning and isinstance(generation_chunk.message, AIMessageChunk):
            generation_chunk.message.additional_kwargs["reasoning_content"] = reasoning

        return generation_chunk
