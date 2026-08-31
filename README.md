# Papyri Assistant

> **Work in progress.** Local chat, agent, SQL, and vector-retrieval paths are implemented and unit tested. Database ingestion, vector-table selection, and embedding-provider setup still require manual configuration.

## Overview

Papyri Assistant is a research chat application for a papyrology database.

- React-based web frontend provides chat, session reset, export, reasoning display, and approve/reject dialogs for interrupted actions.
- FastAPI-based python backend hosts a LangChain/DeepAgents agent with basic agent harness.
- Agent tools inspect/query PostgreSQL and search pgvector with similarity or maximal-marginal-relevance (MMR) retrieval.
- PostgreSQL database supplies papyrus metadata and transcriptions; a separate script creates embeddings usint the pgvector extension.

The backend returns each complete response rather than streaming HTTP events. `new` replaces the current session  **Non-streaming HTTP responses are temporary and tracked in [#12](https://github.com/ssciwr/papyri-assistant/issues/12).**

## Current status

Implemented:

- configurable OpenAI-compatible chat models;
- Hugging Face and VoyageAI embedding/retrieval configurations;
- SQL inspection/query tools and four pgvector search tools;
- resumable approve/reject dialogs for configured agent actions;
- development and TLS-enabled production Compose stacks;
- deterministic backend unit tests with a 90% branch-coverage threshold.

Known limitations:

- One in-memory, process-global session: users are not isolated, checkpoints are not durable, and backend restarts lose the conversation.
- No authentication or authorization.
- The SQL tool accepts free-form SQL. Every call is rolled back, including successful calls, but there is no parser/allow-list gateway and Compose connects as the database owner.
- Embedding generation is a host-side script, not a Compose job; `backend/scripts` is not copied into the backend image.
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
| `backend/configs/default_langchain_embedder.yaml` | Qwen3 embedding model, splitter, and current `embeddings` table contract. |
| `backend/configs/default_langchain_retriever.yaml` | Qwen3 retriever for the current `embeddings` table. **IF YOU USE A DATABASE WITH EMBEDDINGS BUILT VIA `scripts/compute_embeddings.py` WITH `default_langchain_embedder.yaml`, USE THIS ONE.** |
| `backend/configs/legacy_langchain_retriever.yaml` | Existing Scrapyrus/LangChain table. **IF YOU USE A DATABASE WITH SCRAPYRUS-BUILT EMBEDDINGS, USE THIS ONE.** |
| `backend/configs/voyage_ai_langchain_embedder.yaml` | VoyageAI `voyage-4-large` ingestion with 1024-dimensional vectors. |
| `backend/configs/voyage_ai_langchain_retriever.yaml` | Matching VoyageAI retriever for the current `embeddings` table. **IF YOU USE A DATABASE WITH EMBEDDINGS BUILT VIA `scripts/compute_embeddings.py` WITH `voyage_ai_langchain_embedder.yaml`, USE THIS ONE.** |

The config files used can be overridden in the compose files. Per default, the `default_langchain_agent` and voyage-ai configs will be used.

**The embedding and retrieval configurations must agree on provider, model, dimensions, and table columns. Never query vectors with a different model, even when dimensions match.**

### Compose defaults

- Development `compose.yaml` selects the VoyageAI retriever, so its database must contain vectors produced by the matching VoyageAI embedder and `VOYAGE_API_KEY` must be set.
- Production `compose.prod.yaml` selects the legacy retriever for an existing vector table.
- `compose.yaml` currently injects `EMBEDDER_CONFIG`, but the host-side ingestion script reads `EMBEDDINGS_CONFIG`; pass the latter explicitly when running the script.

**The current/legacy distinction is transitional. The current contract mainly adds deterministic chunk IDs and explicit indexed columns.**

## Environment variables

### Required backend values

| Variable | Meaning |
| --- | --- |
| `LLM_API_URL` | OpenAI-compatible API base URL. |
| `LLM_MODEL` | Provider model identifier. |
| `LLM_API_KEY` | Provider key; `EMPTY` is only a construction fallback. |
| `POSTGRES_URL` | psycopg/SQLAlchemy URL used by sessions, tools, retrievers, and ingestion. |

Compose sets its internal URL directly:

```text
postgresql://scrapyrus:scrapyrus@postgres:5432/scrapyrus
```

Host tools cannot resolve `postgres`, so `.env.example` separately provides:

```dotenv
POSTGRES_HOST_URL=postgresql://scrapyrus:scrapyrus@127.0.0.1:55432/scrapyrus
```

The application only reads `POSTGRES_URL`. For host commands, explicitly map the host value: `POSTGRES_URL="$POSTGRES_HOST_URL" ...`.

### Provider and application values

| Variable | Use/default |
| --- | --- |
| `HF_TOKEN` | Optional/required for gated Hugging Face models; Compose preserves the HF cache. |
| `VOYAGE_API_KEY` | Required by VoyageAI configurations and development Compose. |
| `BACKEND_HOST`, `BACKEND_PORT`, `BACKEND_RELOAD` | `0.0.0.0`, `3001`, and optional Uvicorn reload. |
| `CORS_ORIGIN`, `VITE_API_URL` | Browser origins and frontend API URL; development defaults are `http://localhost:5173` and `http://localhost:3001`. |
| `VITE_WARNING_BANNER_TEXT` | Optional banner above the chat. |
| `POSTGRES_DATA_DIR` | PostgreSQL storage; default `./data/postgres`. |
| `POSTGRES_HOST_URL` | Host-side development URL; not read automatically by the backend. |
| `BACKEND_HEALTH_START_PERIOD` | Compose readiness grace period; default 15 minutes for model downloads. |
| `PROD_VITE_API_URL` | Production frontend API URL; default `/api`. |
| `FRONTEND_HTTP_PORT`, `FRONTEND_HTTPS_PORT` | Production ports; defaults `80` and `443`. |
| `TLS_CERTIFICATE_PATH`, `TLS_PRIVATE_KEY_PATH` | Production PEM certificate chain and private key. |

## Database and embeddings

The backend does not create the Scrapyrus source schema. PostgreSQL must have pgvector plus the Scrapyrus `transcriptions`, `orig_dates`, and `orig_places` tables used by the ingestion query.

### Start and populate development PostgreSQL

```sh
cp .env.example .env
docker compose up -d postgres

docker compose run --build --rm scrapyrus scrapyrus metadata ingest
docker compose run --build --rm scrapyrus scrapyrus transcriptions ingest
```

To ingest a host `idp.data` checkout:

```sh
docker compose run --build --rm \
  -v /path/to/idp.data:/data/idp.data:ro \
  scrapyrus scrapyrus --idp-data /data/idp.data metadata ingest
```

Development PostgreSQL is exposed only at `127.0.0.1:55432` and stored in `${POSTGRES_DATA_DIR:-./data/postgres}`. Production PostgreSQL is private to its Compose network.

### Vector schemas

- **Current:** `embeddings`, created/opened by `LangChainEmbeddings`, with deterministic chunk IDs and explicit content, vector, metadata, source, and transcription-ID columns.
- **Legacy:** See `Scrapyrus`

Retrievers only open existing vector tables; they do not create them.

### Build the current vector table

```sh
python -m pip install -e backend
export POSTGRES_HOST_URL=postgresql://scrapyrus:scrapyrus@127.0.0.1:55432/scrapyrus
cd backend
POSTGRES_URL="$POSTGRES_HOST_URL" \
EMBEDDINGS_CONFIG=configs/default_langchain_embedder.yaml \
python scripts/compute_embeddings.py
```

For VoyageAI, replace the config with `configs/voyage_ai_langchain_embedder.yaml` and export `VOYAGE_API_KEY`.

The default Qwen pipeline reads non-empty Scrapyrus transcriptions/translations, joins dates and places, chunks text, embeds with `Qwen/Qwen3-Embedding-8B` at 2000 dimensions, and stores source/transcription metadata. Changing the model, dimensions, splitter, or schema generally requires rebuilding the table and selecting the matching retriever.

## Run locally

```sh
npm install
python -m pip install -e backend
cp .env.example .env
export POSTGRES_HOST_URL=postgresql://scrapyrus:scrapyrus@127.0.0.1:55432/scrapyrus
POSTGRES_URL="$POSTGRES_HOST_URL" npm run dev
```

- Frontend: <http://localhost:5173>
- Backend: <http://localhost:3001>

Startup initializes the agent, embedding model, retriever, and database connection. A missing table/configuration or first model download delays or fails `/health` readiness.

## Run development Compose

```sh
cp .env.example .env
# Set the LLM values and VOYAGE_API_KEY.
docker compose up
```

- Frontend: <http://localhost:5173>
- Backend: <http://localhost:3001>

This uses source bind mounts and a persistent Hugging Face cache. The Scrapyrus tool container runs only through explicit `docker compose run` commands.

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
