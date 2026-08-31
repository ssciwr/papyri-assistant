from typing import Any

import pytest

from papyri_backend.tools import sql


def use_connection(monkeypatch: pytest.MonkeyPatch, connection: Any) -> None:
    monkeypatch.setattr(sql, "connection", lambda: connection)


def test_query_sql_strips_whitespace_returns_rows_and_rolls_back(
    monkeypatch: pytest.MonkeyPatch, fake_connection: Any
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


def test_query_sql_returns_connection_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_to_connect() -> Any:
        raise RuntimeError("session has no connection")

    monkeypatch.setattr(sql, "connection", fail_to_connect)

    result = sql.query_sql.invoke({"query": "SELECT tm_id FROM transcriptions"})

    assert result == (
        "Error, the query attempt failed with error: session has no connection"
    )
