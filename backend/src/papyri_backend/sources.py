# backend/src/papyri_backend/sources.py
"""Resolve documents to the public links the agent cites."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from . import links
from .session import connection

# tm_id is not unique in papyri - one document may have many source files - so
# the rows are grouped and the smallest non-null id of each kind is taken. That
# yields exactly one row per document, and the same row every time.
_LOOKUP = """
    SELECT tm_id,
           min(ddb_hybrid_id) FILTER (WHERE ddb_hybrid_id IS NOT NULL),
           min(dclp_hybrid_id) FILTER (WHERE dclp_hybrid_id IS NOT NULL)
    FROM papyri
    WHERE tm_id = ANY(%s)
    GROUP BY tm_id
"""


def _edition_ids(tm_ids: list[int]) -> dict[int, str | None]:
    """Look up the edition id of every requested document.

    Args:
        tm_ids: Trismegistos numbers, already deduplicated.

    Returns:
        One entry per document found, holding its edition id. An empty mapping
        is returned when the query fails, so that a database problem costs the
        better link rather than every link.
    """
    try:
        session_connection = connection()
        try:
            rows = session_connection.execute(_LOOKUP, (tm_ids,)).fetchall()
        finally:
            # Nothing here writes, and rolling back also clears the aborted
            # state a failed query would otherwise leave on the connection.
            session_connection.rollback()
    except Exception:
        return {}

    return {int(tm_id): ddb or dclp for tm_id, ddb, dclp in rows}


def urls_for(tm_ids: Iterable[Any]) -> dict[int, str]:
    """Find the public link for each of several documents.

    The papyri.info edition is preferred and Trismegistos is the fallback

    Args:
        tm_ids: Trismegistos numbers, in any order and with any repeats.
            Entries that are not positive numbers are ignored.

    Returns:
        One entry per usable id, mapping it to its link.
    """
    wanted: list[int] = []
    for tm_id in tm_ids:
        try:
            number = int(tm_id)
        except (TypeError, ValueError):
            continue
        if number > 0 and number not in wanted:
            wanted.append(number)

    if not wanted:
        return {}

    editions = _edition_ids(wanted)

    urls: dict[int, str] = {}
    for number in wanted:
        url = links.papyri_info_url(editions.get(number)) or links.trismegistos_url(
            number
        )
        if url is not None:
            urls[number] = url

    return urls