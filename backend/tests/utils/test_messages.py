"""Cover the normalization of the message list a chat request arrives with.

The input comes from a client and is typed as ``list[Any]``, so these tests are
mostly about what is thrown away: whatever cannot be read as a role and a piece
of text is dropped rather than raised on, because one odd entry should not fail
a whole conversation.
"""

from __future__ import annotations

from papyri_backend.utils.messages import NormalizedMessage, normalize_messages


def test_normalize_messages_filters_invalid_messages_and_extracts_text() -> None:
    # One list covering every shape the normalizer has to cope with. The first
    # three entries survive, in order; everything after them is dropped.
    normalized = normalize_messages(
        [
            # Surrounding whitespace is trimmed.
            {"role": "system", "content": "  Follow the rules.  "},
            {
                "role": "user",
                # Multi-part content: parts may carry their text under "text" or
                # under "content", or be a bare string. Parts with no readable
                # text contribute nothing and do not produce a blank line.
                "content": [
                    {"text": "Hello"},
                    {"content": "world"},
                    "!",
                    {"text": 123},
                    123,
                ],
            },
            # A single part, not wrapped in a list.
            {"role": "assistant", "content": {"content": "  Reply  "}},
            # Dropped: whitespace-only content is empty once trimmed.
            {"role": "assistant", "content": "   "},
            # Dropped: only system, user and assistant are supported.
            {"role": "tool", "content": "Unsupported role"},
            # Dropped: no role at all.
            {"content": "Missing role"},
            # Dropped: not a mapping.
            "not a mapping",
        ]
    )

    assert normalized == [
        NormalizedMessage(role="system", content="Follow the rules."),
        NormalizedMessage(role="user", content="Hello\nworld\n!"),
        NormalizedMessage(role="assistant", content="Reply"),
    ]


def test_normalize_messages_uses_text_before_content_for_mapping_content() -> None:
    # A part carrying both keys is ambiguous; "text" wins.
    assert normalize_messages(
        [{"role": "user", "content": {"text": "Primary", "content": "Fallback"}}]
    ) == [NormalizedMessage(role="user", content="Primary")]


def test_normalize_messages_returns_empty_list_when_no_supported_content() -> None:
    # Well-formed roles are not enough: a message whose text cannot be read is
    # dropped like any other, and dropping every message yields an empty list
    # rather than an error. The caller is the one that decides that a
    # conversation without a user message is a problem.
    assert (
        normalize_messages(
            [
                {"role": "user", "content": {"text": 123}},
                {"role": "assistant", "content": None},
            ]
        )
        == []
    )
