# Papyri Assistant

> **Work in progress.** Local chat, agent, SQL, and vector-retrieval paths are implemented and unit tested. The database and vector tables must be provisioned outside this application.

## Overview

Papyri Assistant is a research chat application for a papyrology database.

- React-based web frontend provides chat, session reset, export, reasoning display, and approve/reject dialogs for interrupted actions.
- FastAPI-based python backend hosts a LangChain/DeepAgents agent with basic agent harness.
- Agent tools inspect/query PostgreSQL and search pgvector with similarity or maximal-marginal-relevance (MMR) retrieval.
- PostgreSQL supplies externally managed papyrus data and pgvector embeddings.

Assistant responses and reasoning are streamed from LangGraph through the backend to the browser. Completed reasoning remains available in the foldable reasoning panel. `new` replaces the current session.

## Current status

Implemented:

- configurable OpenAI-compatible chat models;
- database-discovered OpenAI, vLLM, MistralAI, VoyageAI, and Hugging Face embeddings;
- SQL inspection/query tools and two text-based pgvector search tools;
- resumable approve/reject dialogs for configured agent actions;
- development and TLS-enabled production Compose stacks;
- deterministic backend unit tests with a 90% branch-coverage threshold.

Known limitations:

- One in-memory, process-global session: users are not isolated, checkpoints are not durable, and backend restarts lose the conversation.
- No authentication or authorization.
- The SQL tool accepts free-form SQL, validates it against the public schema with `sql-data-guard`, and runs it through a database login limited to `SELECT`. This is database-wide read access, not per-user authorization.
- Provider-backed `live_model` tests remain opt-in.

## Requirements

- Node.js 20.19+
- Python 3.11+
- PostgreSQL 16 with pgvector, or Docker Compose
- An OpenAI-compatible chat-model API
- Provider credentials or local model resources required by the specifications in PostgreSQL

## Configuration

YAML `type` values are imported and constructed at runtime. `${VARIABLE}` and `${VARIABLE:-fallback}` expressions are expanded from the environment.

| File | Purpose |
| --- | --- |
| `backend/configs/default_langchain_agent.yaml` | Model, prompt, tools, middleware, interrupts, filesystem permissions, and Deep Agents backends. |
Retriever model and table configuration is not YAML. At startup the backend reads
all three rows from `embedding_table_metadata`, validates the physical
tables, and constructs the allowlisted provider integration described there.
Agent configuration remains in `default_langchain_agent.yaml`.

### Compose defaults

- Both stacks discover transcriptions, translations, and keywords from the same database contract.
- The three stores share one connection-pool engine. Identical specifications also share one query-embedding client.
- Startup fails if any corpus metadata is absent or incomplete, dimensionally inconsistent, or names an unsupported provider.

## Environment variables

### Required backend values

| Variable | Meaning |
| --- | --- |
| `LLM_API_URL` | OpenAI-compatible API base URL. |
| `LLM_MODEL` | Provider model identifier. |
| `LLM_API_KEY` | Provider key; `EMPTY` is only a construction fallback. |
| `POSTGRES_URL` | Read-only psycopg/SQLAlchemy URL used by sessions, SQL tools, and retrievers. |

Compose builds its internal URL from `PAPYRI_QUERY_PASSWORD`:

```text
postgresql://papyri_query_reader:<PAPYRI_QUERY_PASSWORD>@postgres:5432/scrapyrus
```

Host processes cannot resolve `postgres`, so `.env.example` sets the application
variable to the development port published on the host:

```dotenv
POSTGRES_URL=postgresql://papyri_query_reader:${PAPYRI_QUERY_PASSWORD}@127.0.0.1:55432/scrapyrus
```

The application therefore reads the same variable in both environments. The
explicit `POSTGRES_URL` entry in each Compose backend service overrides the
host-side value with its container-network URL.

### Provider and application values

| Variable | Use/default |
| --- | --- |
| `HF_TOKEN` | Optional/required for gated Hugging Face models; Compose preserves the HF cache. |
| `OPENAI_API_KEY`, `VOYAGE_API_KEY`, `MISTRAL_API_KEY`, `VLLM_API_KEY` | Used only when a published corpus selects the corresponding provider. |
| `EMBEDDING_ENDPOINT_<PROFILE>` | Resolves a database `endpoint_profile` without storing routing or secrets in the database; profile names are uppercased and punctuation becomes `_`. `.env.example` and Compose include the default `EMBEDDING_ENDPOINT_VLLM`; add an explicit Compose mapping when using another profile. |
| `BACKEND_HOST`, `BACKEND_PORT`, `BACKEND_RELOAD` | `0.0.0.0`, `3001`, and optional Uvicorn reload. |
| `CORS_ORIGIN`, `VITE_API_URL` | Browser origins and frontend API URL; development defaults are `http://localhost:5173` and `http://localhost:3001`. |
| `VITE_WARNING_BANNER_TEXT` | Optional banner above the chat. |
| `POSTGRES_DATA_DIR` | PostgreSQL storage; default `./data/postgres`. |
| `PAPYRI_QUERY_PASSWORD` | Password for the read-only `papyri_query_reader` login; required in production. Use URL-safe characters. |
| `BACKEND_HEALTH_START_PERIOD` | Compose readiness grace period; default 15 minutes for model downloads. |
| `PROD_VITE_API_URL` | Production frontend API URL; default `/api`. |
| `FRONTEND_HTTP_PORT`, `FRONTEND_HTTPS_PORT` | Production ports; defaults `80` and `443`. |
| `TLS_CERTIFICATE_PATH`, `TLS_PRIVATE_KEY_PATH` | Production PEM certificate chain and private key. |

## Database and embeddings

Papyri Assistant is a reader: Scrapyrus must publish the source tables, all
three embedding tables, and their contract metadata before backend startup.

### Start development PostgreSQL

```sh
cp .env.example .env
docker compose up -d postgres
```

The bundled service starts an empty pgvector-enabled database and the read-only login only; database content must be supplied through infrastructure outside this repository. Development PostgreSQL is exposed only at `127.0.0.1:55432` and stored in `${POSTGRES_DATA_DIR:-./data/postgres}`. Production PostgreSQL is private to its Compose network.

The PostgreSQL image creates `papyri_query_reader` during first-time database initialization. The login has `CONNECT`, public-schema `USAGE`, and `SELECT` on current and future tables owned by `scrapyrus`; it has no table-write or sequence privileges. Initialization scripts do not run again for an existing `${POSTGRES_DATA_DIR}`. To install or refresh the role on an existing development database, run:

```sh
docker compose up -d --force-recreate postgres
docker compose exec postgres /docker-entrypoint-initdb.d/10-query-reader.sh
docker compose up -d --force-recreate backend
```

### Vector schemas

`transcription_embeddings` and `translation_embeddings` expose unique
`chunk_id` values, exact embedded `document_text`, source scalar metadata, and a
dimensioned `embedding` column. `keyword_embeddings` uses the exact keyword text
as both identity and content. For 2,001–4,000 dimensions Scrapyrus additionally
publishes an indexed generated `search_embedding halfvec(n)` column; larger
vectors use exact unindexed search. Cosine distance is fixed.

The real PostgreSQL fixture was verified with LangChain Core 1.6.1,
LangChain Postgres 0.0.17, LangChain OpenAI 1.3.3, Voyage AI 0.4.1,
Hugging Face 1.2.2, and psycopg 3.3.4. Scrapyrus resolves the corresponding
provider integrations from its committed `uv.lock` (including Mistral 1.1.6).

Every vector tool requires a corpus. Text searches return chunks for the two
text corpora and vocabulary candidates for keywords. Vector-input searches also
require the originating specification id and reject mismatched provenance or
dimensions. Scores from different corpora are intentionally not merged.

## Run locally

```sh
npm install
python -m pip install -e backend
cp .env.example .env
npm run dev
```

- Frontend: <http://localhost:5173>
- Backend: <http://localhost:3001>

Startup initializes the agent, query-embedding model, retriever, and read-only database connection. A missing table/configuration or first model download delays or fails `/health` readiness.

## Run development Compose

```sh
cp .env.example .env
# Set the LLM values and VOYAGE_API_KEY.
docker compose up
```

- Frontend: <http://localhost:5173>
- Backend: <http://localhost:3001>

This uses source bind mounts and a persistent Hugging Face cache.

## Run production Compose

```sh
cp .env.example .env
npm run docker:prod
```

Production builds the frontend into nginx, proxies `/api` to the private backend, redirects HTTP to HTTPS, and publishes only nginx. Provide a PEM certificate chain and private key outside git through `TLS_CERTIFICATE_PATH` and `TLS_PRIVATE_KEY_PATH`.

Convert a PKCS#7 chain if needed:

```sh
openssl pkcs7 -print_certs -in your-bundle.p7b -out chain.pem
```

Add `-inform DER` for DER input. Put the server certificate first, followed by the remaining chain.

**Production is not hardened for public or multi-user deployment; review the limitations above before deployment.**

## Tests

```sh
cd backend
python -m pip install -e ".[tests]"
python -m pytest
```

The default suite excludes `integration` and `live_model` markers and enforces 90% global branch coverage.
