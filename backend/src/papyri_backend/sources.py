# backend/src/papyri_backend/sources.py
"""Resolve documents to the public links the agent cites."""

from __future__ import annotations

from collections.abc import Iterable

from . import links
from .session import connection


def _edition_ids(tm_ids: list[int]) -> dict[int, str | None]:
    """Look up the edition id of every requested document.

    Args:
        tm_ids: Trismegistos numbers, already deduplicated.

    Returns:
        One entry per document found, holding its edition id. An empty mapping
        is returned when the query fails, so that a database problem costs the
        better link rather than every link.
    """
    lookup = """
            SELECT tm_id,
                   min(ddb_hybrid_id) FILTER (WHERE ddb_hybrid_id IS NOT NULL),
                   min(dclp_hybrid_id) FILTER (WHERE dclp_hybrid_id IS NOT NULL)
            FROM papyri
            WHERE tm_id = ANY(%s)
            GROUP BY tm_id
        """
    try:
        session_connection = connection()
        try:
            rows = session_connection.execute(lookup, (tm_ids,)).fetchall()
        finally:
            # Nothing here writes, and rolling back also clears the aborted
            # state a failed query would otherwise leave on the connection.
            session_connection.rollback()
    except Exception:
        return {}

    return {int(tm_id): ddb or dclp for tm_id, ddb, dclp in rows}


def urls_for(tm_ids: Iterable[str | int]) -> dict[int, str]:
    """Find the public link for each of several documents.

    The papyri.info edition is preferred and Trismegistos is the fallback

    Args:
        tm_ids: Trismegistos numbers, in any order and with any repeats.

    Returns:
        One entry per usable id, mapping it to its link.
    """
    wanted: list[int] = []
    for tm_id in tm_ids:
        number = int(tm_id)
        if number not in wanted:
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