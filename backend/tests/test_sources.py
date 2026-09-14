# backend/tests/test_sources.py
from typing import Any

import pytest

from papyri_backend import sources

PAPYRI_INFO = "https://papyri.info/editions"
TRISMEGISTOS = "https://www.trismegistos.org/text"


def use_connection(monkeypatch: pytest.MonkeyPatch, connection: Any) -> None:
    monkeypatch.setattr(sources, "connection", lambda: connection)


def test_prefers_the_ddb_edition(
    monkeypatch: pytest.MonkeyPatch, fake_connection: Any
) -> None:
    fake_connection.cursor.rows = [(1885, "p.zen.pestm;;54", None)]
    use_connection(monkeypatch, fake_connection)

    assert sources.urls_for([1885]) == {1885: f"{PAPYRI_INFO}/p.zen.pestm/54"}


def test_uses_the_dclp_edition_when_there_is_no_ddb_one(
    monkeypatch: pytest.MonkeyPatch, fake_connection: Any
) -> None:
    fake_connection.cursor.rows = [(60465, None, "p.iand;5;74")]
    use_connection(monkeypatch, fake_connection)

    assert sources.urls_for([60465]) == {60465: f"{PAPYRI_INFO}/p.iand/5/74"}


def test_falls_back_when_the_document_has_no_edition_id(
    monkeypatch: pytest.MonkeyPatch, fake_connection: Any
) -> None:
    fake_connection.cursor.rows = [(1885, None, None)]
    use_connection(monkeypatch, fake_connection)

    assert sources.urls_for([1885]) == {1885: f"{TRISMEGISTOS}/1885"}


def test_falls_back_when_the_document_is_not_in_papyri(
    monkeypatch: pytest.MonkeyPatch, fake_connection: Any
) -> None:
    fake_connection.cursor.rows = []
    use_connection(monkeypatch, fake_connection)

    assert sources.urls_for([1885]) == {1885: f"{TRISMEGISTOS}/1885"}


def test_falls_back_for_everything_when_the_query_fails(
    monkeypatch: pytest.MonkeyPatch, fake_connection: Any
) -> None:
    fake_connection.execute_error = RuntimeError("database is away")
    use_connection(monkeypatch, fake_connection)

    assert sources.urls_for([1885, 60465]) == {
        1885: f"{TRISMEGISTOS}/1885",
        60465: f"{TRISMEGISTOS}/60465",
    }


def test_asks_for_each_id_once_and_rolls_back(
    monkeypatch: pytest.MonkeyPatch, fake_connection: Any
) -> None:
    fake_connection.cursor.rows = [(1885, "p.zen.pestm;;54", None)]
    use_connection(monkeypatch, fake_connection)

    sources.urls_for([1885, 1885, 60465])

    assert fake_connection.params == [([1885, 60465],)]
    assert fake_connection.rollback_calls == 1


def test_skips_unusable_ids(
    monkeypatch: pytest.MonkeyPatch, fake_connection: Any
) -> None:
    fake_connection.cursor.rows = []
    use_connection(monkeypatch, fake_connection)

    assert sources.urls_for([0, -1, None, "not-a-number"]) == {}


def test_an_empty_request_runs_no_query(
    monkeypatch: pytest.MonkeyPatch, fake_connection: Any
) -> None:
    use_connection(monkeypatch, fake_connection)

    assert sources.urls_for([]) == {}
    assert fake_connection.queries == []