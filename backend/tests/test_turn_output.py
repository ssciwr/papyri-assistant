"""Cover inline reasoning parsing."""

from __future__ import annotations

import pytest

from papyri_backend.langchain_agent import split_streamed_think, split_think


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param(
            "<think>weighing it</think>The answer.",
            ("weighing it", "The answer."),
            id="both-tags",
        ),
        pytest.param(
            "pre-filled trace</think>The answer.",
            ("pre-filled trace", "The answer."),
            id="opening-tag-prefilled-by-template",
        ),
        pytest.param(
            "< THINK >trace</ Think >The answer.",
            ("trace", "The answer."),
            id="spacing-and-casing-vary-by-deployment",
        ),
        pytest.param("Just the answer.", ("", "Just the answer."), id="no-trace"),
        pytest.param("", ("", ""), id="empty"),
    ],
)
def test_split_think(text: str, expected: tuple[str, str]) -> None:
    assert split_think(text) == expected


def test_an_unfinished_explicit_think_block_is_streamed_as_reasoning() -> None:
    assert split_streamed_think("<think>still working") == ("still working", "")


def test_a_prefilled_think_block_is_reasoning_from_its_first_token() -> None:
    assert split_streamed_think("still working", assume_prefilled=True) == (
        "still working",
        "",
    )
