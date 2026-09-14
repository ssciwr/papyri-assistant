# backend/src/papyri_backend/links.py

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

_PAPYRI_INFO = "https://papyri.info/editions/{path}"
_TRISMEGISTOS = "https://www.trismegistos.org/text/{tm_id}"


def papyri_info_url(hybrid_id: Any) -> str | None:
    """Return the papyri.info edition page for a document.
    Args:
        hybrid_id: A ``ddb_hybrid_id`` or ``dclp_hybrid_id``.

    Returns:
        The edition url, or ``None`` when the id is missing or has no usable
        pieces.
    """
    if hybrid_id is None:
        return None

    parts = [part for part in str(hybrid_id).strip().split(";") if part]
    if not parts:
        return None

    return _PAPYRI_INFO.format(path="/".join(parts))


def trismegistos_url(tm_id: Any) -> str | None:
    """Return the Trismegistos page for a document.

    This is the fallback for the handful of documents that carry no edition
    id. Ten documents corpus-wide are in that position.

    Args:
        tm_id: A Trismegistos number, as an int or as its text form. The
            ``transcription_embeddings`` table stores it as TEXT, so both
            arrive in practice.

    Returns:
        The document's Trismegistos url, or ``None`` when the id is missing or
        is not a positive number. Returning ``None`` rather than raising keeps
        a single unusable row from failing a whole search.
    """
    try:
        number = int(tm_id)
    except (TypeError, ValueError):
        return None

    if number <= 0:
        return None

    return _TRISMEGISTOS.format(tm_id=number)


def tm_id_from_metadata(metadata: Mapping[str, Any]) -> int | None:
    """Find a document's Trismegistos number in a chunk's metadata.
    Args:
        metadata: One chunk's metadata.

    Returns:
        The Trismegistos number, or ``None`` when the metadata carries none.
    """
    nested = metadata.get("metadata")
    candidates = [metadata]
    if isinstance(nested, Mapping):
        candidates.append(nested)

    for candidate in candidates:
        try:
            number = int(candidate.get("tm_id"))
        except (TypeError, ValueError):
            continue
        if number > 0:
            return number

    return None