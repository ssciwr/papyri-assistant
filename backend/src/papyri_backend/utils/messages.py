from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

SupportedRole = Literal["system", "user", "assistant"]

_SUPPORTED_ROLES = {"system", "user", "assistant"}


@dataclass(frozen=True)
class NormalizedMessage:
    role: SupportedRole
    content: str


def normalize_messages(messages: list[Any]) -> list[NormalizedMessage]:
    normalized: list[NormalizedMessage] = []

    for message in messages:
        if not isinstance(message, Mapping):
            continue

        role = message.get("role")
        if not isinstance(role, str) or role not in _SUPPORTED_ROLES:
            continue

        content = _extract_text(message.get("content")).strip()
        if not content:
            continue

        normalized.append(NormalizedMessage(role=role, content=content))

    return normalized


def _extract_text(content: Any) -> str:
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        return "\n".join(
            part_text
            for part_text in (_extract_text_from_part(part) for part in content)
            if part_text
        )

    return _extract_text_from_part(content)


def _extract_text_from_part(part: Any) -> str:
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
