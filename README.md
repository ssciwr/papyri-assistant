# Papyri Assistant

> **Work in progress.** Local chat, agent, SQL, and vector-retrieval paths are implemented and unit tested. The database and vector tables must be provisioned outside this application.

## Overview

Papyri Assistant is a research chat application for a papyrology database.

- React-based web frontend provides chat, session reset, export, reasoning display, and approve/reject dialogs for interrupted actions.
- FastAPI-based python backend hosts a LangChain/DeepAgents agent with basic agent harness.
- Agent tools inspect/query PostgreSQL and search pgvector with similarity or maximal-marginal-relevance (MMR) retrieval.
- PostgreSQL supplies externally managed papyrus data and pgvector embeddings.

Assistant responses and reasoning are streamed from LangGraph through the backend to the browser. The foldable reasoning panel embeds a token checkpoint after each model call at its chronological position in the trace, including current context-window pressure, and keeps those checkpoints available after completion. `new` replaces the current session.

Usage checkpoints are provider-reported, so they arrive when each model call finishes rather than for every streamed token. Context percentages use the model profile's `max_input_tokens`; configure that value to match the selected model.
Cached input still counts toward context occupancy. When every model call reports cache-read details, input statistics split uncached and cached tokens; otherwise they explicitly note that cached tokens are included in the input total.

## Current status

Implemented:

- configurable OpenAI-compatible chat models;
- Hugging Face and VoyageAI query-embedding/retrieval configurations;
- SQL inspection/query tools and four pgvector search tools;
- resumable approve/reject dialogs for configured agent actions;
- development and TLS-enabled production Compose stacks;
- deterministic backend unit tests with a 90% branch-coverage threshold.

Known limitations:

- One in-memory, process-global session: users are not isolated, checkpoints are not durable, and backend restarts lose the conversation.
- No authentication or authorization.
- The SQL tool accepts free-form SQL, validates it against the public schema with `sql-data-guard`, and runs it through a database login limited to `SELECT`. This is database-wide read access, not per-user authorization.
- Real-service `integration` and `live_model` test lanes are marked but not yet implemented.

## Requirements

- Node.js 20.19+
- Python 3.11+
- PostgreSQL 16 with pgvector, or Docker Compose
- An OpenAI-compatible chat-model API
- Storage and memory for the selected embedding model; the default Qwen model is a large first download

## Configuration

YAML `type` values are imported and constructed at runtime. `${VARIABLE}` and `${VARIABLE:-fallback}` expressions are expanded from the environment.

| File | Purpose |
| --- | --- |
| `backend/configs/default_langchain_agent.yaml` | Model, prompt, tools, middleware, interrupts, filesystem permissions, and Deep Agents backends. |
| `backend/configs/default_langchain_retriever.yaml` | Qwen3 retriever for an externally populated `embeddings` table containing 2000-dimensional Qwen3 vectors. |
| `backend/configs/legacy_langchain_retriever.yaml` | VoyageAI retriever for Scrapyrus `transcription_embeddings`, mapped directly to Scrapyrus columns and filtered to `voyage-4-large`. **IF YOU USE A DATABASE WITH SCRAPYRUS-BUILT VOYAGEAI EMBEDDINGS, USE THIS ONE. CURRENTLY UNTESTED.** |
| `backend/configs/voyage_ai_langchain_retriever.yaml` | VoyageAI retriever for an externally populated `embeddings` table containing 1024-dimensional `voyage-4-large` vectors. |

The config files used can be overridden in the compose files. Per default, the `default_langchain_agent` and voyage-ai configs will be used.

**The query-embedding model and stored vectors must agree on provider, model, and dimensions. Never query vectors with a different model, even when dimensions match.**

### Compose defaults

- Development `compose.yaml` selects `voyage_ai_langchain_retriever.yaml`, which reads the Papyri Assistant `embeddings` table.
- Production `compose.prod.yaml` selects `legacy_langchain_retriever.yaml`, which reads Scrapyrus `transcription_embeddings` directly.
- Both VoyageAI paths require `VOYAGE_API_KEY` and stored `voyage-4-large` vectors at 1024 dimensions.

**The current retriever can query only one embedding table at a time because one configuration creates one `PGVectorStore`. The shipped Scrapyrus config queries `transcription_embeddings`; change its `table_name` to `translation_embeddings` to query translations instead. Both tables cannot be queried concurrently by the current backend. This is a temporary limitation and will change in the future (tracked [here](https://github.com/ssciwr/papyri-assistant/issues/21))**

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

Host tools cannot resolve `postgres`, so `.env.example` separately provides:

```dotenv
POSTGRES_HOST_URL=postgresql://papyri_query_reader:<PAPYRI_QUERY_PASSWORD>@127.0.0.1:55432/scrapyrus
```

The application only reads `POSTGRES_URL`. For host application commands, explicitly map the read-only host value: `POSTGRES_URL="$POSTGRES_HOST_URL" ...`.

### Provider and application values

| Variable | Use/default |
| --- | --- |
| `HF_TOKEN` | Optional/required for gated Hugging Face models; Compose preserves the HF cache. |
| `VOYAGE_API_KEY` | Required by VoyageAI configurations and development Compose. |
| `BACKEND_HOST`, `BACKEND_PORT`, `BACKEND_RELOAD` | `0.0.0.0`, `3001`, and optional Uvicorn reload. |
| `CORS_ORIGIN`, `VITE_API_URL` | Browser origins and frontend API URL; development defaults are `http://localhost:5173` and `http://localhost:3001`. |
| `VITE_WARNING_BANNER_TEXT` | Optional banner above the chat. |
| `POSTGRES_DATA_DIR` | PostgreSQL storage; default `./data/postgres`. |
| `PAPYRI_QUERY_PASSWORD` | Password for the read-only `papyri_query_reader` login; required in production. Use URL-safe characters. |
| `POSTGRES_HOST_URL` | Host-side read-only URL; not read automatically by the backend. |
| `BACKEND_HEALTH_START_PERIOD` | Compose readiness grace period; default 15 minutes for model downloads. |
| `PROD_VITE_API_URL` | Production frontend API URL; default `/api`. |
| `FRONTEND_HTTP_PORT`, `FRONTEND_HTTPS_PORT` | Production ports; defaults `80` and `443`. |
| `TLS_CERTIFICATE_PATH`, `TLS_PRIVATE_KEY_PATH` | Production PEM certificate chain and private key. |

## Database and embeddings

Papyri Assistant never creates, populates, resets, or migrates application data. PostgreSQL must already contain the source and vector tables selected by the agent and retriever configurations.

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

- **Generic:** `embeddings`, an externally managed table with explicit content, vector, metadata, source, and transcription-ID columns. The default and VoyageAI retriever configs target this table with their matching models.
- **Scrapyrus:** `transcription_embeddings` and `translation_embeddings`. Each row contains `xml_id`, `model_name`, `chunk_index`, `source_path`, `tm_id`, `language`, `document_text`, `input_hash`, `embedding`, and `updated_at`. `legacy_langchain_retriever.yaml` directly maps LangChain to `transcription_embeddings` and filters retrieval to `voyage-4-large`.

Retrievers only open existing vector tables; they do not create them. **Only one of the Scrapyrus embedding tables can be selected at a time with the current single-retriever backend.**

## Run locally

```sh
npm install
python -m pip install -e backend
cp .env.example .env
export POSTGRES_HOST_URL=postgresql://papyri_query_reader:replace-with-a-long-random-password@127.0.0.1:55432/scrapyrus
POSTGRES_URL="$POSTGRES_HOST_URL" npm run dev
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
