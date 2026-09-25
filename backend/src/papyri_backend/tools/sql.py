"""Let the agent inspect and query the postgres database."""

from langchain.tools import tool
from sql_data_guard import verify_sql

from ..session import connection
from .. import sources


_SCHEMA_QUERY = """
    SELECT table_name, column_name, data_type
    FROM information_schema.columns
    WHERE table_schema = 'public'
    ORDER BY table_name, ordinal_position
    """


def _rows(query: str) -> list[tuple] | str:
    """Run a read query and return its rows.

    Args:
        query: The sql to run.

    Returns:
        The rows, or the error text if the query failed. The error is returned
        rather than raised so that the model can read it and try again.
    """
    try:
        session_connection = connection()
        try:
            return session_connection.execute(query).fetchall()
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
    """List all tables in a pre-connected postgres database.

    Returns:
        One table name per line.
    """
    rows = _rows(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_type = 'BASE TABLE'
        ORDER BY table_name
        """
    )
    if isinstance(rows, str):
        return rows
    return "\n".join(table_name for (table_name,) in rows)


@tool(parse_docstring=True)
def inspect_sql() -> str:
    """Get all sql tables and their schema for inspection and orientation.

    Returns:
        One ``table.column: datatype`` line per column, over every table.
    """
    rows = _rows(_SCHEMA_QUERY)
    if isinstance(rows, str):
        return rows
    return "\n".join(f"{table}.{column}: {kind}" for table, column, kind in rows)


def _guard_config() -> dict | str:
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


@tool(parse_docstring=True)
def get_source_links(tm_ids: list[int]) -> str:
    """Look up the public edition link of one or more documents.

    Use this for documents you found with ``query_sql``.

    Args:
        tm_ids: The Trismegistos numbers of the documents you want to cite.

    Returns:
        One line per requested document, in the order asked. A document whose
        link could not be resolved gets a line saying so, so that a missing
        link is visible to you rather than silently absent.
    """
    if not tm_ids:
        return "No tm_ids were given, so there is nothing to look up."

    wanted: list[int] = []
    unusable: list[str] = []
    for tm_id in tm_ids:
        try:
            wanted.append(int(tm_id))
        except (TypeError, ValueError):
            unusable.append(str(tm_id))

    urls = sources.urls_for(wanted)

    lines = [
        f"TM {tm_id}: {urls[tm_id]}"
        if tm_id in urls
        else f"TM {tm_id}: no link could be resolved for this document"
        for tm_id in wanted
    ]
    lines += [f"{value}: not a Trismegistos number" for value in unusable]
    return "\n".join(lines)