from typing import Any

import pytest

from papyri_backend.tools import sql


def use_connection(monkeypatch: pytest.MonkeyPatch, connection: Any) -> None:
    monkeypatch.setattr(sql, "connection", lambda: connection)


@pytest.fixture
def guard_config(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    config = {
        "tables": [
            {
                "table_name": "transcriptions",
                "columns": ["tm_id", "source_path"],
            }
        ]
    }
    monkeypatch.setattr(sql, "_guard_config", lambda: config)
    return config


def test_query_sql_strips_whitespace_returns_rows_and_rolls_back(
    monkeypatch: pytest.MonkeyPatch, fake_connection: Any, guard_config: Any
) -> None:
    rows = [(12345, "P.Oxy. 1.1")]
    fake_connection.cursor.rows = rows
    use_connection(monkeypatch, fake_connection)

    result = sql.query_sql.invoke(
        {"query": "  SELECT tm_id, source_path FROM transcriptions\n"}
    )

    assert result == rows
    assert fake_connection.queries == ["SELECT tm_id, source_path FROM transcriptions"]
    assert fake_connection.rollback_calls == 1


def test_guard_config_uses_public_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sql,
        "_rows",
        lambda query: [
            ("orig_dates", "date_id", "integer"),
            ("transcriptions", "tm_id", "integer"),
            ("transcriptions", "source_path", "text"),
        ],
    )

    assert sql._guard_config() == {
        "tables": [
            {"table_name": "orig_dates", "columns": ["date_id"]},
            {
                "table_name": "transcriptions",
                "columns": ["tm_id", "source_path"],
            },
        ]
    }


@pytest.mark.parametrize(
    ("schema_result", "expected"),
    [
        ("Error, schema unavailable", "Error, schema unavailable"),
        ([], "Error, SQL query validation failed: no public tables are available"),
    ],
)
def test_guard_config_returns_schema_errors(
    monkeypatch: pytest.MonkeyPatch,
    schema_result: list[tuple] | str,
    expected: str,
) -> None:
    monkeypatch.setattr(sql, "_rows", lambda query: schema_result)

    assert sql._guard_config() == expected


def test_query_sql_returns_guard_config_errors(
    monkeypatch: pytest.MonkeyPatch, fake_connection: Any
) -> None:
    monkeypatch.setattr(sql, "_guard_config", lambda: "Error, schema unavailable")
    use_connection(monkeypatch, fake_connection)

    assert sql.query_sql.invoke({"query": "SELECT 1"}) == "Error, schema unavailable"
    assert fake_connection.queries == []


def test_query_sql_rejects_invalid_query_before_execution(
    monkeypatch: pytest.MonkeyPatch, fake_connection: Any, guard_config: Any
) -> None:
    use_connection(monkeypatch, fake_connection)

    result = sql.query_sql.invoke({"query": "DELETE FROM transcriptions"})

    assert (
        result == "Error, SQL query validation failed: DELETE statement is not allowed"
    )
    assert fake_connection.queries == []
    assert fake_connection.rollback_calls == 0


def test_list_sql_tables_formats_one_table_per_line(
    monkeypatch: pytest.MonkeyPatch, fake_connection: Any
) -> None:
    fake_connection.cursor.rows = [("orig_dates",), ("transcriptions",)]
    use_connection(monkeypatch, fake_connection)

    result = sql.list_sql_tables.invoke({})

    assert result == "orig_dates\ntranscriptions"
    assert "information_schema.tables" in fake_connection.queries[0]
    assert fake_connection.rollback_calls == 1


def test_inspect_sql_formats_table_columns(
    monkeypatch: pytest.MonkeyPatch, fake_connection: Any
) -> None:
    fake_connection.cursor.rows = [
        ("transcriptions", "tm_id", "integer"),
        ("transcriptions", "source_path", "text"),
        ("orig_places", "place", "text"),
    ]
    use_connection(monkeypatch, fake_connection)

    result = sql.inspect_sql.invoke({})

    assert result == (
        "transcriptions.tm_id: integer\n"
        "transcriptions.source_path: text\n"
        "orig_places.place: text"
    )
    assert "information_schema.columns" in fake_connection.queries[0]
    assert fake_connection.rollback_calls == 1


@pytest.mark.parametrize(
    ("tool", "arguments"),
    [
        (sql.list_sql_tables, {}),
        (sql.inspect_sql, {}),
    ],
)
def test_schema_tools_return_query_errors(
    monkeypatch: pytest.MonkeyPatch,
    fake_connection: Any,
    tool: Any,
    arguments: dict[str, Any],
) -> None:
    fake_connection.execute_error = RuntimeError("database unavailable")
    use_connection(monkeypatch, fake_connection)

    result = tool.invoke(arguments)

    assert result == "Error, the query attempt failed with error: database unavailable"
    assert fake_connection.rollback_calls == 1


@pytest.mark.parametrize(
    ("failure_field", "message"),
    [
        ("execute_error", "invalid SQL"),
        ("fetch_error", "fetch failed"),
    ],
)
def test_query_sql_rolls_back_and_returns_errors(
    monkeypatch: pytest.MonkeyPatch,
    fake_connection: Any,
    guard_config: Any,
    failure_field: str,
    message: str,
) -> None:
    if failure_field == "execute_error":
        fake_connection.execute_error = RuntimeError(message)
    else:
        fake_connection.cursor.error = RuntimeError(message)
    use_connection(monkeypatch, fake_connection)

    result = sql.query_sql.invoke({"query": "SELECT tm_id FROM transcriptions"})

    assert result == f"Error, the query attempt failed with error: {message}"
    assert fake_connection.rollback_calls == 1


def test_query_sql_returns_connection_errors(
    monkeypatch: pytest.MonkeyPatch, guard_config: Any
) -> None:
    def fail_to_connect() -> Any:
        raise RuntimeError("session has no connection")

    monkeypatch.setattr(sql, "connection", fail_to_connect)

    result = sql.query_sql.invoke({"query": "SELECT tm_id FROM transcriptions"})

    assert result == (
        "Error, the query attempt failed with error: session has no connection"
    )

@pytest.fixture
def link_lookups(monkeypatch: pytest.MonkeyPatch) -> list[list[int]]:
    """Record the batches of ids looked up, resolving everything but TM 999."""
    lookups: list[list[int]] = []

    def fake_urls_for(tm_ids: Any) -> dict[int, str]:
        wanted = [int(tm_id) for tm_id in tm_ids]
        lookups.append(wanted)
        return {
            tm_id: f"https://papyri.info/editions/p.test/{tm_id}"
            for tm_id in wanted
            if tm_id != 999
        }

    monkeypatch.setattr(sql.sources, "urls_for", fake_urls_for)
    return lookups

def test_get_source_links_formats_one_line_per_id(
    link_lookups: list[list[int]],
) -> None:
    result = sql.get_source_links.invoke({"tm_ids": [12345, 678]})

    assert result == (
        "TM 12345: https://papyri.info/editions/p.test/12345\n"
        "TM 678: https://papyri.info/editions/p.test/678"
    )
    assert link_lookups == [[12345, 678]]


def test_get_source_links_when_a_document_has_no_link(
    link_lookups: list[list[int]],
) -> None:
    result = sql.get_source_links.invoke({"tm_ids": [999, 12345]})

    assert result.splitlines() == [
        "TM 999: no link could be resolved for this document",
        "TM 12345: https://papyri.info/editions/p.test/12345",
    ]

def test_get_source_links_handles_an_empty_request() -> None:
    assert sql.get_source_links.invoke({"tm_ids": []}) == (
        "No tm_ids were given, so there is nothing to look up."
    )

