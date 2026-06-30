from __future__ import annotations

import asyncio
import sys
import types
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from papyri_backend import chat
from papyri_backend.utils.messages import NormalizedMessage


def test_provider_kwargs_requires_api_key(monkeypatch) -> None:
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    with pytest.raises(ValueError, match="Set LLM_API_KEY"):
        chat._provider_kwargs()


def test_provider_kwargs_includes_optional_base_url(monkeypatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_API_URL", "https://example.test/v1")

    assert chat._provider_kwargs() == {
        "api_key": "test-key",
        "base_url": "https://example.test/v1",
    }


@pytest.mark.parametrize(
    ("role", "expected_type"),
    [
        ("assistant", AIMessage),
        ("system", SystemMessage),
        ("user", HumanMessage),
    ],
)
def test_to_langchain_message_uses_role_specific_classes(role, expected_type) -> None:
    converted = chat._to_langchain_message(
        NormalizedMessage(role=role, content="Hello")
    )

    assert isinstance(converted, expected_type)
    assert converted.content == "Hello"


def test_find_last_user_message_index() -> None:
    messages = [
        NormalizedMessage(role="system", content="Rules"),
        NormalizedMessage(role="user", content="First"),
        NormalizedMessage(role="assistant", content="Reply"),
        NormalizedMessage(role="user", content="Second"),
    ]

    assert chat._find_last_user_message_index(messages) == 3
    assert chat._find_last_user_message_index(messages[:1]) == -1


def test_stringify_model_content_handles_strings_lists_and_mappings() -> None:
    assert chat._stringify_model_content("plain") == "plain"
    assert (
        chat._stringify_model_content(
            [
                {"text": "one"},
                {"content": "two"},
                {"ignored": "value"},
                "three",
            ]
        )
        == "one\ntwo\nthree"
    )
    assert chat._stringify_model_content(123) == "123"


def test_answer_with_chat_requires_a_user_message() -> None:
    with pytest.raises(ValueError, match="No user message found"):
        asyncio.run(
            chat.answer_with_chat(
                [
                    {"role": "system", "content": "Rules"},
                    {"role": "assistant", "content": "Reply"},
                ]
            )
        )


def test_answer_with_chat_sends_context_window_to_model(monkeypatch) -> None:
    class FakeChatOpenAI:
        instances: list["FakeChatOpenAI"] = []

        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs
            self.instances.append(self)

    class FakeMessagesPlaceholder:
        def __init__(self, variable_name: str) -> None:
            self.variable_name = variable_name

    class FakeChain:
        payload: dict[str, object] | None = None

        def __init__(self, model: FakeChatOpenAI) -> None:
            self.model = model

        async def ainvoke(self, payload: dict[str, object]) -> SimpleNamespace:
            self.payload = payload
            FakeChain.payload = payload
            return SimpleNamespace(
                content=[{"text": "answer"}, {"content": "extra"}, "tail"]
            )

    class FakePrompt:
        created_messages: list[object] | None = None

        @classmethod
        def from_messages(cls, messages: list[object]) -> "FakePrompt":
            cls.created_messages = messages
            return cls()

        def __or__(self, model: FakeChatOpenAI) -> FakeChain:
            return FakeChain(model)

    fake_langchain_openai = types.ModuleType("langchain_openai")
    fake_langchain_openai.ChatOpenAI = FakeChatOpenAI

    monkeypatch.setitem(sys.modules, "langchain_openai", fake_langchain_openai)
    monkeypatch.setattr(chat, "ChatPromptTemplate", FakePrompt)
    monkeypatch.setattr(chat, "MessagesPlaceholder", FakeMessagesPlaceholder)
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_API_URL", "https://example.test/v1")
    monkeypatch.setenv("LLM_MODEL", "test-model")

    result = asyncio.run(
        chat.answer_with_chat(
            [{"role": "user", "content": f"message {index}"} for index in range(12)]
        )
    )

    assert result == {"text": "answer\nextra\ntail"}
    assert FakeChatOpenAI.instances[0].kwargs == {
        "model": "test-model",
        "temperature": 0.2,
        "api_key": "test-key",
        "base_url": "https://example.test/v1",
    }
    assert FakePrompt.created_messages is not None
    assert FakePrompt.created_messages[0] == ("system", chat._DEFAULT_SYSTEM_PROMPT)
    assert isinstance(FakePrompt.created_messages[1], FakeMessagesPlaceholder)
    assert FakePrompt.created_messages[1].variable_name == "messages"
    assert FakeChain.payload is not None
    assert [message.content for message in FakeChain.payload["messages"]] == [
        f"message {index}" for index in range(3, 12)
    ]
