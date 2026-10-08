"""Let the agent inspect and query the postgres database."""

import json
from typing import Any

from langchain.tools import tool
from sql_data_guard import verify_sql

from ..session import connection


_SCHEMA_QUERY = """
    SELECT table_name, column_name, data_type
    FROM information_schema.columns
    WHERE table_schema = 'public'
    ORDER BY table_name, ordinal_position
    """

_CATALOG_SCHEMA_VERSION = 1
_CATALOG_TABLE = "scrapyrus_semantic_catalog"

_TABLE_SUMMARIES_QUERY = f"""
    SELECT
        catalog.table_name,
        catalog.catalog_schema_version,
        catalog.semantics
    FROM public.{_CATALOG_TABLE} AS catalog
    JOIN information_schema.tables AS live_table
      ON live_table.table_schema = catalog.schema_name
     AND live_table.table_name = catalog.table_name
     AND live_table.table_type = 'BASE TABLE'
    WHERE catalog.schema_name = 'public'
      AND catalog.table_name <> '{_CATALOG_TABLE}'
    ORDER BY catalog.table_name
    """

_TABLE_SEMANTICS_QUERY = f"""
    SELECT
        live_table.table_schema,
        live_table.table_name,
        catalog.catalog_schema_version,
        catalog.producer_version,
        catalog.updated_at,
        catalog.semantics
    FROM information_schema.tables AS live_table
    LEFT JOIN public.{_CATALOG_TABLE} AS catalog
      ON catalog.schema_name = live_table.table_schema
     AND catalog.table_name = live_table.table_name
    WHERE live_table.table_schema = 'public'
      AND live_table.table_type = 'BASE TABLE'
      AND live_table.table_name <> '{_CATALOG_TABLE}'
      AND live_table.table_name = %s
    """


def _rows(query: str, params: tuple[Any, ...] | None = None) -> list[tuple] | str:
    """Run a read query and return its rows.

    Args:
        query: The sql to run.
        params: Values for placeholders in the query.

    Returns:
        The rows, or the error text if the query failed. The error is returned
        rather than raised so that the model can read it and try again.
    """
    try:
        session_connection = connection()
        try:
            return session_connection.execute(query, params).fetchall()
        finally:
            # Nothing here writes, so every query is ended by rolling it back.
            # That is also what clears the aborted state a failed query leaves
            # behind, which would otherwise block every later query on this
            # connection.
            session_connection.rollback()
    except Exception as e:
        return f"Error, the query attempt failed with error: {e}"


@tool(parse_docstring=True)
def list_sql_tables() -> str:
    """List live domain tables and summarize what each table is useful for.

    Returns:
        One table name, description, and list of uses per entry.
    """
    rows = _rows(_TABLE_SUMMARIES_QUERY)
    if isinstance(rows, str):
        return rows
    summaries = []
    for table_name, catalog_schema_version, semantics in rows:
        error = _semantic_catalog_error(table_name, catalog_schema_version, semantics)
        if error is not None:
            return error

        summary = f"{table_name}: {semantics['description']}"
        useful_for = semantics.get("useful_for") or []
        if useful_for:
            summary += f" Useful for: {'; '.join(useful_for)}."
        summaries.append(summary)
    return "\n".join(summaries)


def _semantic_catalog_error(
    table_name: str, catalog_schema_version: Any, semantics: Any
) -> str | None:
    """Return an error for a semantic catalog entry this consumer cannot use."""

    if catalog_schema_version != _CATALOG_SCHEMA_VERSION:
        return (
            f"Error, table {table_name!r} uses unsupported semantic catalog schema "
            f"version {catalog_schema_version!r}; expected {_CATALOG_SCHEMA_VERSION}"
        )
    if not isinstance(semantics, dict):
        return f"Error, table {table_name!r} has invalid semantic catalog data"
    if not isinstance(semantics.get("description"), str):
        return f"Error, table {table_name!r} has no semantic description"
    return None


@tool(parse_docstring=True)
def inspect_sql_table(table_name: str) -> str:
    """Inspect one live table's complete semantics.

    Args:
        table_name: Unqualified name of a table in the public schema.

    Returns:
        The table's versioned semantic catalog entry.
    """
    table_name = table_name.strip()
    if not table_name:
        return "Error, table_name must not be blank"

    rows = _rows(_TABLE_SEMANTICS_QUERY, (table_name,))
    if isinstance(rows, str):
        return rows
    if not rows:
        return f"Error, public table {table_name!r} does not exist"

    (
        schema_name,
        live_table_name,
        catalog_schema_version,
        producer_version,
        updated_at,
        semantics,
    ) = rows[0]
    if catalog_schema_version is None:
        return f"Error, public table {table_name!r} has no semantic catalog entry"
    error = _semantic_catalog_error(live_table_name, catalog_schema_version, semantics)
    if error is not None:
        return error

    result = {
        "schema_name": schema_name,
        "table_name": live_table_name,
        "catalog_schema_version": catalog_schema_version,
        "producer_version": producer_version,
        "catalog_updated_at": updated_at,
        "semantics": semantics,
    }
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


def _guard_config() -> dict | str:
    """Build the SQL guard configuration from the public schema."""
    rows = _rows(_SCHEMA_QUERY)
    if isinstance(rows, str):
        return rows

    columns_by_table: dict[str, list[str]] = {}
    for table, column, _ in rows:
        columns_by_table.setdefault(table, []).append(column)
    if not columns_by_table:
        return "Error, SQL query validation failed: no public tables are available"

    return {
        "tables": [
            {"table_name": table, "columns": columns}
            for table, columns in columns_by_table.items()
        ]
    }


@tool(parse_docstring=True)
def query_sql(query: str) -> list[tuple] | str:
    """Query the connected sql database and return the result.

    Args:
        query: The sql statement to run.

    Returns:
        The rows the query returned, or the error text if validation or execution
        failed.
    """
    query = query.strip()
    config = _guard_config()
    if isinstance(config, str):
        return config

    validation = verify_sql(query, config, dialect="postgres")
    if not validation["allowed"]:
        errors = "; ".join(sorted(validation["errors"]))
        return f"Error, SQL query validation failed: {errors}"
    return _rows(query)
