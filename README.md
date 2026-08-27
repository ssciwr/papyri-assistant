# Papyri Assistant

> **Work in progress.** The core local chat, agent, SQL, and vector-retrieval paths are implemented and unit tested. Database/model integration and the embedding-provider setup still need setup adjustments by hand.

## What it is

Papyri Assistant is a research chat application for working with a papyrology database.

- The React/assistant-ui frontend provides chat, conversation reset, export, reasoning display, and approval dialogs for interrupted actions.
- The FastAPI backend owns a LangChain/Deep Agents agent.
- The agent can inspect/query PostgreSQL and search a pgvector store with similarity or maximal-marginal-relevance (MMR) retrieval.
- Scrapyrus supplies the papyrus metadata and transcription tables. Embeddings are built separately and stored in PostgreSQL.

The browser talks to `POST /chat`; the backend runs the agent and returns a complete response rather than streaming HTTP events. `/new` replaces the current backend session and `/health` reports process health.
**The non-streaming behavior is temporary and will most likely change in the future (issue [[#12](https://github.com/ssciwr/papyri-assistant/issues/12)]).

## Current status and limitations

Implemented:

- configurable OpenAI-compatible chat model;
- configurable Hugging Face and VoyageAI embedding/retrieval adapters;
- SQL inspection/query tools and four pgvector search tools;
- resumable approve/reject dialogs for configured agent actions;
- development and TLS-enabled production Compose stacks;
- deterministic backend unit suite.

Still missing or incomplete:

- The process has one in-memory, process-global agent session. Checkpoints are not durable, multiple users are not isolated, and restarting the backend loses the conversation.
- There is no authentication or authorization layer.
- The SQL tool accepts free-form SQL. It rolls every call back, including successful calls, but there is currently no SQL parser/allow-list gateway and Compose connects as the database owner.
- Embedding generation is a manual host-side script; it is not currently a Compose job and `backend/scripts` is not copied into the backend image.
- The current agent hard stops when the context window of the model is full. Recovery is only possible via a new session.

## Requirements

For local development:

- Node.js 20.19 or newer
- Python 3.11 or newer
- PostgreSQL 16 with pgvector, or Docker with Compose
- An OpenAI-compatible chat-model API
- Enough storage and memory for the selected embedding model. The default Qwen model is a large download and can make first startup slow.

## Configuration files

Configuration is YAML-based. Import paths under `type` are resolved and constructed at runtime; `${VARIABLE}` and `${VARIABLE:-fallback}` expressions are expanded from the environment.

| File | Purpose |
| --- | --- |
| `backend/configs/default_langchain_agent.yaml` | Chat model, system prompt, tools, middleware, interrupts, filesystem permissions, and Deep Agents backends. |
| `backend/configs/default_langchain_embedder.yaml` | Hugging Face Qwen3 embedding model, text splitter, and the current `embeddings` table contract. |
| `backend/configs/default_langchain_retriever.yaml` | Retriever matching the current Hugging Face embedder and `embeddings` table. |
| `backend/configs/legacy_langchain_retriever.yaml` | Compatibility mapping for an existing LangChain collection table named `langchain_pg_embedding` which has been built with the scarpyrus project. |
| `backend/configs/voyage_ai_langchain_embedder.yaml` | VoyageAI `voyage-4-large` ingestion configured for 1024-dimensional vectors. |
| `backend/configs/voyage_ai_langchain_retriever.yaml` | Matching VoyageAI retriever for the current `embeddings` table. |

Override the server defaults with:

```sh
AGENT_CONFIG=/absolute/or/working-directory-relative/agent.yaml
RETRIEVER_CONFIG=/absolute/or/working-directory-relative/retriever.yaml
```

If unset, a locally started backend uses `default_langchain_agent.yaml` and `default_langchain_retriever.yaml`.

**The embedding and retrieval configurations must agree on the provider/model and table columns.** Vectors produced by one model must not be queried with another model, even when their dimensions happen to match.

### Current Compose peculiarity

Both Compose files explicitly select `legacy_langchain_retriever.yaml`. That is for databases containing the older `langchain_pg_embedding` schema. The current embedding script writes the newer `embeddings` table instead. **This distinction will disappear in the future. The new contract mainly adds a chunk_id index and is in part an artifact of an earlier development stage.**

Use the Voyage retriever path instead only when the table was embedded with the matching Voyage model.

## Environment variables

### Required backend values

| Variable | Meaning |
| --- | --- |
| `LLM_API_URL` | Base URL of the OpenAI-compatible chat API. |
| `LLM_MODEL` | Chat-model identifier sent to the provider. |
| `LLM_API_KEY` | Provider key. The config has an `EMPTY` construction fallback, but a real provider normally requires a key. |
| `POSTGRES_URL` | psycopg/SQLAlchemy URL used by the session, SQL tools, retriever, and embedding builder. |

Compose injects the container-network URL directly as `POSTGRES_URL`:

```text
postgresql://scrapyrus:scrapyrus@postgres:5432/scrapyrus
```

Host-side tools cannot resolve the Compose service name `postgres`, so `.env.example` also defines the separately named URL for the published development port:

```dotenv
POSTGRES_HOST_URL=postgresql://scrapyrus:scrapyrus@127.0.0.1:55432/scrapyrus
```

The backend and embedding adapters deliberately continue to consume only `POSTGRES_URL`. When running them on the host, explicitly pass the host URL as `POSTGRES_URL`, for example `POSTGRES_URL="$POSTGRES_HOST_URL" ...` after exporting or sourcing `POSTGRES_HOST_URL`.

### Embedding-provider values

| Variable | When needed |
| --- | --- |
| `EMBEDDINGS_CONFIG` | Required by `backend/scripts/compute_embeddings.py`; points to an embedder YAML file. |
| `HF_TOKEN` | Optional/required for gated Hugging Face models and authenticated downloads. Compose passes it and preserves the Hugging Face cache in a named volume. |
| `VOYAGE_API_KEY` | Required by the VoyageAI configurations. Compose passes it from the root environment when set. |

### Optional application and deployment values

| Variable | Default/use |
| --- | --- |
| `AGENT_CONFIG` | Shipped default agent config. |
| `RETRIEVER_CONFIG` | Shipped default retriever locally; Compose currently pins the legacy config. |
| `WORKSPACE_DIR`, `MEMORY_DIR` | Host paths backing the agent's `/workspace` and `/memory` routes. |
| `BACKEND_HOST` | `0.0.0.0` |
| `BACKEND_PORT` | `3001` |
| `BACKEND_RELOAD` | Enables Uvicorn reload for truthy values. |
| `CORS_ORIGIN` | Comma-separated browser origins; development default is `http://localhost:5173`. |
| `VITE_API_URL` | Frontend backend URL; development default is `http://localhost:3001`. |
| `VITE_WARNING_BANNER_TEXT` | Optional banner shown above the chat. |
| `POSTGRES_DATA_DIR` | `./data/postgres` |
| `POSTGRES_HOST_URL` | Host-side connection URL for the PostgreSQL port published by development Compose. It is not read automatically by the backend. |
| `BACKEND_HEALTH_START_PERIOD` | Compose health-check grace period; defaults to 15 minutes because model download can be slow. |
| `PROD_VITE_API_URL` | `/api` in production. |
| `FRONTEND_HTTP_PORT`, `FRONTEND_HTTPS_PORT` | `80` and `443`. |
| `TLS_CERTIFICATE_PATH`, `TLS_PRIVATE_KEY_PATH` | Production nginx certificate and private-key files. |

## Database setup

The backend does not create the Scrapyrus source schema. It expects a pgvector-enabled PostgreSQL database populated with Scrapyrus metadata and transcriptions, including the `transcriptions`, `orig_dates`, and `orig_places` tables used by the current embedding query.

### Development database and ingestion

Create `.env`, include the LLM values, then start PostgreSQL. Compose supplies its internal `POSTGRES_URL`; `POSTGRES_HOST_URL` is only for commands run directly on the host.

```sh
cp .env.example .env
docker compose up -d postgres
```

Load Scrapyrus data with the one-off management image:

```sh
docker compose run --build --rm scrapyrus scrapyrus metadata ingest
docker compose run --build --rm scrapyrus scrapyrus transcriptions ingest
```

To ingest from a host `idp.data` checkout:

```sh
docker compose run --build --rm \
  -v /path/to/idp.data:/data/idp.data:ro \
  scrapyrus scrapyrus --idp-data /data/idp.data metadata ingest
```

The database is exposed only on `127.0.0.1:55432` in development and persisted in `${POSTGRES_DATA_DIR:-./data/postgres}`. The production database is private to the Compose network.

### Current and legacy vector schemas

There are two supported layouts during the transition:

- **Current:** `embeddings`, created/opened by `LangChainEmbeddings` using the table contract in the embedder config. It uses deterministic text chunk IDs and explicit content, vector, metadata, source, and transcription-ID columns.
- **Legacy:** `langchain_pg_embedding`, read through `legacy_langchain_retriever.yaml` for an existing LangChain collection-style database.

The retriever only opens an existing vector table; it does not create one. Run embedding ingestion before switching to the current retriever.

### Build the current embedding table

Install the backend locally, select the database and embedder configuration, and run the script from `backend/`:

```sh
python -m pip install -e backend
export POSTGRES_HOST_URL=postgresql://scrapyrus:scrapyrus@127.0.0.1:55432/scrapyrus
cd backend
POSTGRES_URL="$POSTGRES_HOST_URL" \
EMBEDDINGS_CONFIG=configs/default_langchain_embedder.yaml \
python scripts/compute_embeddings.py
```

The default pipeline:

- reads non-empty transcriptions/translations from Scrapyrus;
- joins aggregated dates and places;
- splits text into overlapping chunks;
- embeds with `Qwen/Qwen3-Embedding-8B`, truncated to 2000 dimensions and normalized;
- creates/opens the configured `embeddings` table and stores source/transcription metadata with every chunk.

The `vector_size`, model output, and database column must agree. Changing the embedding model, dimensions, splitter, or table contract generally requires rebuilding the vector data and using a matching retriever config.

## Run locally

```sh
npm install
python -m pip install -e backend
cp .env.example .env
# Export the LLM settings, then map the documented host URL explicitly.
export POSTGRES_HOST_URL=postgresql://scrapyrus:scrapyrus@127.0.0.1:55432/scrapyrus
POSTGRES_URL="$POSTGRES_HOST_URL" npm run dev
```

- Frontend: <http://localhost:5173>
- Backend: <http://localhost:3001>

The backend starts its agent, embedding model, retriever, and PostgreSQL connection during application startup. A missing table/configuration or a large first model download therefore delays or fails `/health` readiness.

## Run with Docker Compose

```sh
cp .env.example .env
# Configure the LLM values; Compose supplies the internal POSTGRES_URL.
npm run docker:up
```

- Frontend: <http://localhost:5173>
- Backend: <http://localhost:3001>

This uses `compose.yaml` with source bind mounts. The Hugging Face cache survives container recreation. The Scrapyrus tool container is only started for explicit `docker compose run` commands.

## Run production Compose

```sh
cp .env.example .env
npm run docker:prod
```

Production uses `compose.prod.yaml`, builds the frontend into nginx, proxies `/api` to the private backend, redirects HTTP to HTTPS, and publishes only the frontend.

Provide a PEM certificate chain and private key outside git through `TLS_CERTIFICATE_PATH` and `TLS_PRIVATE_KEY_PATH`. If a provider supplied a PKCS#7 (`.p7b`) chain, convert it first, for example:

```sh
openssl pkcs7 -print_certs -in your-bundle.p7b -out chain.pem
```

Add `-inform DER` for a DER-encoded bundle. Concatenate the server certificate first and the remaining chain afterward into the file referenced by `TLS_CERTIFICATE_PATH`.

Production is not hardened for public or multi-user deployment; review the limitations above first.

## Tests

```sh
cd backend
python -m pip install -e ".[tests]"
python -m pytest
```

The default command excludes `integration` and `live_model` tests and enforces 90% global branch coverage. The real-service integration lane remains planned rather than implemented.
