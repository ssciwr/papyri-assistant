#!/bin/sh
set -eu

: "${PAPYRI_QUERY_PASSWORD:?PAPYRI_QUERY_PASSWORD must be set}"

psql --set ON_ERROR_STOP=1 \
    --username "$POSTGRES_USER" \
    --dbname "$POSTGRES_DB" \
    --set reader_password="$PAPYRI_QUERY_PASSWORD" \
    --set database_name="$POSTGRES_DB" \
    --set owner_role="$POSTGRES_USER" <<'SQL'
DO $setup$
BEGIN
    IF NOT EXISTS (
        SELECT FROM pg_catalog.pg_roles WHERE rolname = 'papyri_query_reader'
    ) THEN
        CREATE ROLE papyri_query_reader;
    END IF;
END
$setup$;

SELECT format(
    'ALTER ROLE papyri_query_reader WITH LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS',
    :'reader_password'
) \gexec

ALTER ROLE papyri_query_reader SET default_transaction_read_only = on;

GRANT CONNECT ON DATABASE :"database_name" TO papyri_query_reader;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO papyri_query_reader;

REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM papyri_query_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO papyri_query_reader;
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM papyri_query_reader;

ALTER DEFAULT PRIVILEGES FOR ROLE :"owner_role" IN SCHEMA public
    GRANT SELECT ON TABLES TO papyri_query_reader;

-- Keep writes and sequence access out of the default privilege set too.
ALTER DEFAULT PRIVILEGES FOR ROLE :"owner_role" IN SCHEMA public
    REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER ON TABLES
    FROM papyri_query_reader;
ALTER DEFAULT PRIVILEGES FOR ROLE :"owner_role" IN SCHEMA public
    REVOKE ALL PRIVILEGES ON SEQUENCES FROM papyri_query_reader;
SQL
