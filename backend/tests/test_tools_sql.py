import json
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


def test_rows_passes_query_parameters_and_rolls_back(
    monkeypatch: pytest.MonkeyPatch, fake_connection: Any
) -> None:
    fake_connection.cursor.rows = [("transcriptions",)]
    use_connection(monkeypatch, fake_connection)

    result = sql._rows("SELECT table_name FROM example WHERE table_name = %s", ("x",))

    assert result == [("transcriptions",)]
    assert fake_connection.params == [("x",)]
    assert fake_connection.rollback_calls == 1


def test_list_sql_tables_formats_semantic_summaries(
    monkeypatch: pytest.MonkeyPatch, fake_connection: Any
) -> None:
    fake_connection.cursor.rows = [
        (
            "orig_dates",
            1,
            {
                "description": "Dates assigned to papyri.",
                "useful_for": ["date filtering", "chronological analysis"],
            },
        ),
        (
            "transcriptions",
            1,
            {
                "description": "Source and searchable text.",
                "useful_for": ["full-text search"],
            },
        ),
    ]
    use_connection(monkeypatch, fake_connection)

    result = sql.list_sql_tables.invoke({})

    assert result == (
        "orig_dates: Dates assigned to papyri. Useful for: date filtering; "
        "chronological analysis.\n"
        "transcriptions: Source and searchable text. Useful for: full-text search."
    )
    assert "information_schema.tables" in fake_connection.queries[0]
    assert "scrapyrus_semantic_catalog" in fake_connection.queries[0]
    assert (
        "catalog.table_name <> 'scrapyrus_semantic_catalog'"
        in (fake_connection.queries[0])
    )
    assert fake_connection.rollback_calls == 1


def test_list_sql_tables_rejects_unsupported_catalog_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sql,
        "_rows",
        lambda query, params=None: [("transcriptions", 2, {"description": "Text"})],
    )

    result = sql.list_sql_tables.invoke({})

    assert result == (
        "Error, table 'transcriptions' uses unsupported semantic catalog schema "
        "version 2; expected 1"
    )


def test_inspect_sql_table_returns_semantics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    semantics = {
        "table_name": "transcriptions",
        "description": "Source and searchable text.",
        "row_grain": "One textual division.",
        "useful_for": ["full-text search"],
        "aliases": [],
        "columns": {"tm_id": {"description": "Trismegistos document ID."}},
        "relationships": [],
        "caveats": ["A document can have multiple rows."],
    }
    calls = []

    def rows(query: str, params: tuple[Any, ...] | None = None) -> list[tuple]:
        calls.append((query, params))
        assert query == sql._TABLE_SEMANTICS_QUERY
        return [
            (
                "public",
                "transcriptions",
                1,
                "2.3.4",
                "2026-10-08 12:00:00+00:00",
                semantics,
            )
        ]

    monkeypatch.setattr(sql, "_rows", rows)

    result = sql.inspect_sql_table.invoke({"table_name": " transcriptions "})

    assert json.loads(result) == {
        "schema_name": "public",
        "table_name": "transcriptions",
        "catalog_schema_version": 1,
        "producer_version": "2.3.4",
        "catalog_updated_at": "2026-10-08 12:00:00+00:00",
        "semantics": semantics,
    }
    assert [params for _, params in calls] == [("transcriptions",)]


@pytest.mark.parametrize(
    ("catalog_rows", "expected"),
    [
        ([], "Error, public table 'missing' does not exist"),
        (
            [("public", "missing", None, None, None, None)],
            "Error, public table 'missing' has no semantic catalog entry",
        ),
        (
            [("public", "missing", 2, "1.0", "now", {"description": "x"})],
            "Error, table 'missing' uses unsupported semantic catalog schema version "
            "2; expected 1",
        ),
    ],
)
def test_inspect_sql_table_reports_unavailable_semantics(
    monkeypatch: pytest.MonkeyPatch,
    catalog_rows: list[tuple],
    expected: str,
) -> None:
    monkeypatch.setattr(sql, "_rows", lambda query, params=None: catalog_rows)

    assert sql.inspect_sql_table.invoke({"table_name": "missing"}) == expected


def test_inspect_sql_table_rejects_blank_name() -> None:
    assert sql.inspect_sql_table.invoke({"table_name": "  "}) == (
        "Error, table_name must not be blank"
    )


@pytest.mark.parametrize(
    ("tool", "arguments"),
    [
        (sql.list_sql_tables, {}),
        (sql.inspect_sql_table, {"table_name": "transcriptions"}),
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
