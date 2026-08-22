import os  # for getting postgres specs

import psycopg
from langchain.tools import tool

from ..verify import sql as sql_verify


@tool
def list_sql_tables():
    """
    List all tables in a pre-connected postgres database.
    """
    POSTGRES_URL = os.getenv("POSTGRES_URL")
    if POSTGRES_URL is None:
        raise RuntimeError("Error, database url env variable not set")
    with psycopg.connect(POSTGRES_URL) as conn:
        try:
            rows = conn.execute(
                "SELECT name FROM information_schema.columns WHERE table_schema = 'public'"
            )

            schema_text = "\n".join(f"{table}" for table in rows)

            return schema_text
        except Exception as e:
            response = f"Error, the query attempt failed with error: {e}"
            return [{"message": response}]


@tool
def inspect_sql():
    """
    Get all sql tables and their schema for inspection and orientation.
    Returns a string that contains 'table.column: datatype' for each table and column therein.
    Tool has no input, and outputs a single formatted string.
    """
    POSTGRES_URL = os.getenv("POSTGRES_URL")
    if POSTGRES_URL is None:
        raise RuntimeError("Error, database url env variable not set")
    SCHEMA_SQL = """
    SELECT table_name, column_name, data_type
    FROM information_schema.columns
    WHERE table_schema = 'public'
    ORDER BY table_name, ordinal_position
    """
    with psycopg.connect(POSTGRES_URL) as conn:
        try:
            rows = conn.execute(SCHEMA_SQL).fetchall()

            schema_text = "\n".join(
                f"{table}.{column}: {datatype}" for table, column, datatype in rows
            )

            return schema_text
        except Exception as e:
            response = f"Error, the query attempt failed with error: {e}"
            return [{"message": response}]


@tool
def query_sql(query) -> list:
    """Query an already connected sql database and return the result or the error message.
    Connect to a database defined via POSTGRES_URL POSTGRES_USER POSTGRES_PW env variables.
    first if not already there.
    """

    POSTGRES_URL = os.getenv("POSTGRES_URL")
    if POSTGRES_URL is None:
        raise RuntimeError("Error, database url env variable not set")
    query = query.strip()

    sql_verify.sql_query_verifier(query)
    response = "nothing"
    with psycopg.connect(POSTGRES_URL) as db, db.cursor() as cursor:
        try:
            result = cursor.execute(query).fetchall()
            return result
        except Exception as e:
            response = f"Error, the query attempt failed with error: {e}"
            return [{"message": response}]
