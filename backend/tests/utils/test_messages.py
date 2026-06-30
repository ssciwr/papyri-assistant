from __future__ import annotations

from papyri_backend.utils.messages import NormalizedMessage, normalize_messages


def test_normalize_messages_filters_invalid_messages_and_extracts_text() -> None:
    normalized = normalize_messages(
        [
            {"role": "system", "content": "  Follow the rules.  "},
            {
                "role": "user",
                "content": [
                    {"text": "Hello"},
                    {"content": "world"},
                    "!",
                    {"text": 123},
                    123,
                ],
            },
            {"role": "assistant", "content": {"content": "  Reply  "}},
            {"role": "assistant", "content": "   "},
            {"role": "tool", "content": "Unsupported role"},
            {"content": "Missing role"},
            "not a mapping",
        ]
    )

    assert normalized == [
        NormalizedMessage(role="system", content="Follow the rules."),
        NormalizedMessage(role="user", content="Hello\nworld\n!"),
        NormalizedMessage(role="assistant", content="Reply"),
    ]


def test_normalize_messages_uses_text_before_content_for_mapping_content() -> None:
    assert normalize_messages(
        [{"role": "user", "content": {"text": "Primary", "content": "Fallback"}}]
    ) == [NormalizedMessage(role="user", content="Primary")]


def test_normalize_messages_returns_empty_list_when_no_supported_content() -> None:
    assert (
        normalize_messages(
            [
                {"role": "user", "content": {"text": 123}},
                {"role": "assistant", "content": None},
            ]
        )
        == []
    )
