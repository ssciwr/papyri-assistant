"""Let the agent inspect and query the postgres database."""

import os
from contextlib import contextmanager

import psycopg
from langchain.tools import tool


@contextmanager
def _connection():
    """Open a connection to the configured database.

    Yields:
        A connection to the database named by ``POSTGRES_URL``.

    Raises:
        RuntimeError: ``POSTGRES_URL`` is not set.
    """
    url = os.getenv("POSTGRES_URL")
    if url is None:
        raise RuntimeError("Error, database url env variable not set")
    with psycopg.connect(url) as connection:
        yield connection


def _rows(query: str) -> list[tuple] | str:
    """Run a read query and return its rows.

    Args:
        query: The sql to run.

    Returns:
        The rows, or the error text if the query failed. The error is returned
        rather than raised so that the model can read it and try again.
    """
    try:
        with _connection() as connection:
            return connection.execute(query).fetchall()
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
    rows = _rows(
        """
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position
        """
    )
    if isinstance(rows, str):
        return rows
    return "\n".join(f"{table}.{column}: {kind}" for table, column, kind in rows)


@tool(parse_docstring=True)
def query_sql(query: str) -> list[tuple] | str:
    """Query the connected sql database and return the result.

    Args:
        query: The sql statement to run.

    Returns:
        The rows the query returned, or the error text if it failed.
    """
    return _rows(query.strip())
