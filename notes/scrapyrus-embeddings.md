# Scrapyrus embeddings: pipeline, export, and LangChain swap

Notes on how the `scrapyrus` project (`~/Development/scrapyrus`) builds and stores
embeddings, how to move the whole database to another machine, and which parts
could be replaced by the LangChain `Embeddings` interface with Qwen3-Embedding-8B.

All source paths below are relative to the `scrapyrus` checkout unless noted.

## 1. Where the code lives and how embeddings are built

### Code

- `src/scrapyrus/transcriptions/embeddings.py` — the whole pipeline
- `src/scrapyrus/transcriptions/llms.py` — inference-server provider layer
- `src/scrapyrus/__main__.py:325-545` — CLI group
  `scrapyrus embeddings {ingest,update,delete,dump,import,evaluate}`

### Where the data comes from — not from files

Embedding ingestion never touches `idp.data`. The chain is two stages:

1. `scrapyrus transcriptions ingest --idp-data …` walks the idp.data clone
   (`DDbDP`, `Translations`, `HGV_meta_EpiDoc`) and writes the `transcriptions`
   table — schema at `src/scrapyrus/transcriptions/core.py:59-76`. It stores raw
   `xml_content` (Postgres `xml` type), `tm_id`, `source_path`, `type`
   (`transcription` | `translation`), `language`, plus a plain-text `text` column
   and generated `tsvector`s for BM25.
2. `scrapyrus embeddings ingest` reads `xml_content` back out of that table
   (`_select_xml_rows`, embeddings.py:495) and embeds it.

So transcriptions ingest must run first, otherwise ingestion stops with
`TranscriptionsUnavailableError`.

### How a vector gets made

Per row, in `setup_store` (embeddings.py:101):

1. **XML → text** via Saxon XSLT. Transcriptions go through `epidoc-to-text.xsl`
   with `MAXIMUM_TRANSCRIPTION_OPTIONS` (core.py:28) — `abbrev`, `lost`,
   `unclear`, `regularize` all on, `break_on_gap` off, i.e. the fullest possible
   reading. Translations go through `translation-epidoc-to-text.xsl`.
2. **Chunking** by `chunk_embedding_text` (embeddings.py:421): whitespace words,
   default 500 per chunk, 10% overlap (step 450). Documents of 500 words or
   fewer are passed through byte-identical, unchunked.
3. **Hash** — sha256 of the chunk into `input_hash`, which is what
   `--stale-only` / `embeddings update` compares against to skip unchanged work.
4. **Embed** — `_embed_document` (embeddings.py:736) → `provider.embed(text)`.
   One HTTP POST per chunk, strictly serial, no batching. Context-length errors
   from the server are caught and the chunk is skipped with a printed message;
   anything else aborts the run.
5. **Provider selection** — `initialize_llm_provider` (llms.py:108) is a chain of
   responsibility matched on *hostname*: `api.mistral.ai`, `api.openai.com`,
   `api.voyageai.com`, and otherwise `VLLMProvider`, which probes `GET /version`
   and claims the URL if it answers. No match at all raises `ValueError`.

### Where they are saved

Two Postgres tables, `transcription_embeddings` and `translation_embeddings`,
created by `_ensure_embedding_schema` (embeddings.py:537):

```
xml_id, model_name, chunk_index, source_path, tm_id, language,
document_text, input_hash, embedding vector, updated_at
PRIMARY KEY (xml_id, model_name, chunk_index)
```

`embedding vector` is declared **without** a dimension, so several models can
coexist in one table, keyed by `model_name`.

After each run, `_recreate_embedding_index` (embeddings.py:654) builds a
*partial* HNSW index per model — `vector_cosine_ops` up to 2000 dims,
`halfvec_cosine_ops` up to 4000, and **above 4000 it silently creates nothing**.
See section 3.

## 2. Exporting the whole database

Everything — SQL tables, vectors, indexes — lives in the one Postgres database,
so a single `pg_dump` covers it. There is already a script pair in the scrapyrus
repo: `scripts/postgres_dump.sh` / `scripts/postgres_restore.sh` (custom format,
`--exit-on-error --single-transaction`).

From the papyri-assistant compose setup, dump straight out of the running
container so no local `pg_dump` matching the server version is needed:

```sh
docker exec papyri-dev-postgres-1 sh -c \
  'pg_dump --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" --format=custom' \
  > scrapyrus.dump
```

On the target machine, bring up the same pgvector image, then:

```sh
docker exec -i papyri-dev-postgres-1 sh -c \
  'pg_restore --clean --if-exists --no-owner --exit-on-error --single-transaction \
     --username="$POSTGRES_USER" --dbname="$POSTGRES_DB"' \
  < scrapyrus.dump
```

Three things that will bite:

- The target server **must have pgvector installed** (`pgvector/pgvector:pg16`
  does). The dump contains `CREATE EXTENSION vector`; without the server package
  the restore fails.
- Use `--no-owner` unless the `scrapyrus` role exists on the target under the
  same name.
- HNSW indexes are rebuilt from scratch during restore. On a full corpus that is
  the slow part, not the data load.

### Alternative: physical copy

Copying `./data/postgres` (the bind mount from `compose.yaml:16`) wholesale is a
physical copy: only valid with the container stopped, and only into the identical
PostgreSQL major version and architecture. It is faster for a big corpus since
indexes come along as-is. Prefer `pg_dump` unless dump/restore time actually
hurts.

### Alternative: vectors only

To move only embeddings between existing databases:

```sh
scrapyrus embeddings dump   --model-name X --kind transcription
scrapyrus embeddings import --model-name X --kind transcription
```

These use Postgres *binary COPY* of the embedding rows (embeddings.py:273).
Per-model, per-kind, and dimension consistency is validated on import.

## 3. Swapping in LangChain + Qwen3-Embedding-8B

### First: LangChain may not be needed at all

`VLLMProvider` is the fallback for any URL that answers `GET /version`, and it
POSTs to `/v1/embeddings`. Serve Qwen3-Embedding-8B on vLLM, point
`--inference-server-url` at it, and the existing code works unchanged — zero code
change. Via `host.docker.internal` it already reaches a host-side server, per the
papyri-assistant README.

### Seams to replace, if LangChain is wanted anyway

Reasons to want it: HuggingFace/Ollama backends, or unifying with
`backend/src/papyri_backend/langchain_agent.py`.

- `EmbeddingStore.__init__` (embeddings.py:97) and `_embed` (embeddings.py:233) —
  swap `initialize_llm_provider` for any `langchain_core.embeddings.Embeddings`.
  Two-line change; `_embed` becomes `self.embeddings.embed_query(text)`. The
  entire `llms.py` provider chain then becomes dead code for the embedding path.
- `_embed_documents` (embeddings.py:712) — the real win. The current loop is one
  serial HTTP request per chunk. LangChain's `embed_documents(list[str])`
  batches, which on a full corpus is the difference between hours and minutes.
- `chunk_embedding_text` (embeddings.py:421) — optional, could become a
  `TokenTextSplitter`. Note the current word-count splitter is deterministic and
  feeds `input_hash`; changing it invalidates every stored chunk and forces a
  full re-embed.

### Do not replace the storage layer

LangChain's `PGVector` vector store imposes its own
`langchain_pg_embedding` / `langchain_pg_collection` schema, which would break
the `dump`/`import` binary COPY commands, the per-model partial HNSW indexes, the
chunk-level staleness logic, and `evaluate_embeddings`. Keep pgvector access
as-is and swap only the embedding *function*.

### The Qwen3-8B specific problem: 4096 dimensions

4096 is above `HNSW_HALFVEC_MAX_DIMENSIONS = 4000` (embeddings.py:60), so
`_recreate_embedding_index` hits the bare `return` at embeddings.py:663 and
**builds no index at all, silently**. Ingestion appears to succeed and every
similarity query degrades to a sequential scan over the corpus.

That constant is not arbitrary — 4000 is pgvector's hard ceiling for `halfvec`
HNSW, so raising it does not help.

The fix is Qwen3's Matryoshka support: it is trained for dimension truncation, so
request 2048 (`dimensions=2048` on the vLLM/OpenAI-compatible call, or
`truncate_dim` on the HF/sentence-transformers path). 2048 still exceeds the
`vector` limit of 2000 but lands inside `halfvec`, so a real HNSW index gets
built. To use the `vector_cosine_ops` path instead, truncate to 1024.

### Two smaller Qwen3 notes

- It expects an **instruction prefix on queries only**
  (`Instruct: <task>\nQuery: <text>`), documents unprefixed. LangChain's
  `embed_query` vs `embed_documents` split maps onto that cleanly, whereas the
  current single `embed()` is used for both.
- L2-normalize the output, since the index uses cosine ops.
