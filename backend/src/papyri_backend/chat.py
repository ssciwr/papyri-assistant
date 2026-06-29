from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from .utils.messages import NormalizedMessage, normalize_messages

_DEFAULT_SYSTEM_PROMPT = "You are a concise, helpful assistant."
_MAX_CONTEXT_MESSAGES = 9


async def answer_with_chat(raw_messages: list[Any]) -> dict[str, str]:
    messages = normalize_messages(raw_messages)
    last_user_message_index = _find_last_user_message_index(messages)

    if last_user_message_index == -1:
        raise ValueError("No user message found.")

    start_index = max(0, last_user_message_index - (_MAX_CONTEXT_MESSAGES - 1))
    window = messages[start_index : last_user_message_index + 1]
    conversation = [_to_langchain_message(message) for message in window]

    from langchain_openai import ChatOpenAI

    model = ChatOpenAI(
        model=_get_required_env(
            "LLM_MODEL", "Set LLM_MODEL in backend/.env before using /chat."
        ),
        temperature=0.2,
        **_provider_kwargs(),
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", _DEFAULT_SYSTEM_PROMPT),
            MessagesPlaceholder("messages"),
        ]
    )
    chain = prompt | model

    response = await chain.ainvoke({"messages": conversation})

    return {"text": _stringify_model_content(response.content)}


def _provider_kwargs() -> dict[str, str]:
    api_key = _get_required_env(
        "LLM_API_KEY", "Set LLM_API_KEY in backend/.env before using /chat."
    )
    kwargs = {"api_key": api_key}
    api_url = _get_env("LLM_API_URL")

    if api_url:
        kwargs["base_url"] = api_url

    return kwargs


def _get_required_env(name: str, message: str) -> str:
    value = _get_env(name)
    if not value:
        raise ValueError(message)

    return value


def _get_env(name: str) -> str | None:
    value = os.getenv(name)
    if value:
        return value

    return None


def _to_langchain_message(message: NormalizedMessage) -> BaseMessage:
    if message.role == "assistant":
        return AIMessage(content=message.content)

    if message.role == "system":
        return SystemMessage(content=message.content)

    return HumanMessage(content=message.content)


def _find_last_user_message_index(messages: list[NormalizedMessage]) -> int:
    for index in range(len(messages) - 1, -1, -1):
        if messages[index].role == "user":
            return index

    return -1


def _stringify_model_content(content: Any) -> str:
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        return "\n".join(
            part_text
            for part_text in (_stringify_content_part(part) for part in content)
            if part_text
        )

    return str(content)


def _stringify_content_part(part: Any) -> str:
    if isinstance(part, str):
        return part

    if not isinstance(part, Mapping):
        return ""

    text = part.get("text")
    if isinstance(text, str):
        return text

    content = part.get("content")
    if isinstance(content, str):
        return content

    return ""
