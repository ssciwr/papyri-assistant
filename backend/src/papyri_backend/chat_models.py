"""Chat model adapters used by the Papyri assistant."""

from typing import Any

import httpx
from langchain_core.messages import AIMessageChunk
from langchain_core.outputs import ChatGenerationChunk
from langchain_openai import ChatOpenAI
from pydantic import PrivateAttr


class MaybeVLLMChatOpenAI(ChatOpenAI):
    """Preserve reasoning chunks when an OpenAI-compatible endpoint is vLLM."""

    _is_vllm: bool = PrivateAttr(default=False)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        base_url = str(self.root_client.base_url).rstrip("/").removesuffix("/v1")
        api_key = self.openai_api_key.get_secret_value()
        response = httpx.get(
            f"{base_url}/version",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=5.0,
        )
        self._is_vllm = response.status_code == 200 and "version" in response.json()

    def _convert_chunk_to_generation_chunk(
        self,
        chunk: dict,
        default_chunk_class: type,
        base_generation_info: dict | None,
    ) -> ChatGenerationChunk | None:
        generation_chunk = super()._convert_chunk_to_generation_chunk(
            chunk, default_chunk_class, base_generation_info
        )
        if generation_chunk is None or not self._is_vllm:
            return generation_chunk

        generation_chunk.message.response_metadata["model_provider"] = "vllm"
        choices = chunk.get("choices") or chunk.get("chunk", {}).get("choices") or []
        delta = choices[0].get("delta") if choices else None
        reasoning = delta.get("reasoning") if delta else None
        if reasoning and isinstance(generation_chunk.message, AIMessageChunk):
            generation_chunk.message.additional_kwargs["reasoning_content"] = reasoning

        return generation_chunk
