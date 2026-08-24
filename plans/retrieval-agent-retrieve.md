# Plan: `RetrievalAgent.retrieve` compatible with `answer_with_chat`

## Context

`chat.py` can run in two modes. In `"agentic"` mode it calls
[LangChainAgent.run_single_turn](backend/src/papyri_backend/langchain_agent.py#L560),
which returns exactly what the `/chat` endpoint's `ChatResponse` model expects:
`{"text": str, "reasoning": str, "interrupt": InterruptView | None}`.

In `"retrieval"` mode it calls
[RetrievalAgent.retrieve](backend/src/papyri_backend/langchain_agent.py#L82), which
today returns `self.retriever.batch([query])` — a **list of lists of
`Document`**, not a dict. FastAPI would fail to serialize it. It is also handed
`raw_messages[-1]`, a message dict, not a string.

Goal: make `retrieve` a drop-in sibling of `run_single_turn` — same input shape,
same output shape — and make retrieval mode actually reachable.

## Changes

### 1. `RetrievalAgent.retrieve` — `backend/src/papyri_backend/langchain_agent.py`

Replace the current body with a turn-shaped method:

```python
def retrieve(self, message) -> dict[str, Any]:
    """Answer one turn by returning the retrieved chunks as markdown.

    Mirrors LangChainAgent.run_single_turn's contract so the /chat endpoint
    can call either without knowing which mode it is in.
    """
```

Steps:

1. **Extract the query** the same way `run_single_turn` does:
   `text = message["content"][0]["text"]`. Accept a plain `str` too (`if
   isinstance(message, str)`), so the smoke-test/CLI path stays easy.
2. **Retrieve**: `docs = self.retriever.invoke(query)` — a flat `list[Document]`.
   Use `invoke`, not `batch([query])`; the batch wrapper only exists to produce
   the nested list that caused the mismatch.
3. **Format** via a new `@staticmethod _format_documents(docs) -> str` (see
   below).
4. **Wrap errors** like `run_single_turn` does: catch `Exception` and put
   `f"Retrieval failed: {exc}"` into `text`, since failures deliberately travel
   as chat output during local development.
5. **Return** `{"text": ..., "reasoning": "", "interrupt": None}`. Both extra
   keys are constants — a retriever has no trace and cannot pause — but they
   keep the response shape identical, so `ChatResponse` validates unchanged.

Empty result set → `text` = `"No matching passages were found."` (never an
empty string; an empty assistant bubble reads as a bug in the UI).

### 2. `_format_documents` — markdown, because the frontend renders markdown

[ChatThread.tsx](frontend/src/components/ChatThread.tsx#L28) pipes assistant text
through `react-markdown` + `remark-gfm`, so markdown is the right target.

Per document, emit:

```
**1. TM 12345** — `DDbDP/.../foo.xml` (chunk 2)

> chunk text, blockquoted line by line

---
```

Rules:

- The heading line is built **defensively** from `doc.metadata` with `.get`:
  prefer `tm_id`, fall back to `source_path`, fall back to `id`, fall back to
  just the index. Append `chunk_index`, `language`, and the similarity score
  (`score` / `relevance_score` — only present for some search types) when they
  exist. Never `KeyError`.
- Body: `doc.page_content`, with each line prefixed `"> "` so a multi-line chunk
  stays inside one blockquote, and blank interior lines become `">"`.
- Join documents with `"\n\n---\n\n"`.
- Prepend a one-line header: `f"Retrieved {len(docs)} passage(s) for: {query}"`.

Keep it a pure `staticmethod` on `RetrievalAgent` taking `(docs, query)` so it
is unit-testable without a database.

### 3. Make retrieval mode reachable — `backend/src/papyri_backend/chat.py`

Three bugs sit between the endpoint and this code:

- [switch_mode_to](backend/src/papyri_backend/chat.py#L22) accepts only
  `"agentic"` / `"basic"`, while `new_agent` and `answer_with_chat` branch on
  `"retrieval"`. Change the allowed set to `{"agentic", "retrieval"}` (and the
  error message with it) so the mode can actually be entered.
- [new_agent](backend/src/papyri_backend/chat.py#L44)'s retrieval branch loads
  the same `CONFIG` yaml as the deepagent, whose top-level key is `kwargs:` and
  whose contents are deepagent settings. `make_langchain_retriever` passes the
  loaded mapping straight into `RetrievalAgent(**config)` and would raise
  `TypeError`. Add a separate `RETRIEVER_CONFIG = os.getenv("RETRIEVER_CONFIG",
  "configs/default_langchain_retriever.yaml")` and use it in that branch.
- `new_agent`'s retrieval branch is missing `global agent` (it is declared only
  inside the `agentic` branch, which happens to cover the whole function in
  Python — verify and hoist the `global agent` to the top of the function for
  clarity).

`answer_with_chat` itself needs **no change** once `retrieve` returns the dict:
`answer = agent.retrieve(raw_messages[-1])` already passes the right thing.

### 4. New config file — `backend/configs/default_langchain_retriever.yaml`

Flat mapping matching `RetrievalAgent.__init__`:

```yaml
embeddingmodel: Qwen/Qwen3-Embedding-8B   # or whatever is served
embeddings_type: langchain_huggingface.HuggingFaceEmbeddings
ps_connection: null            # falls back to POSTGRES_URL
search_type: similarity
store_kwargs:
  collection_name: transcription_embeddings
embedding_kwargs: {}
search_kwargs:
  k: 5
```

Note `ps_connection` is read into `ps_conn` for the None-check but
[line 79](backend/src/papyri_backend/langchain_agent.py#L79) passes the original
`ps_connection` to `PGVector` — fix that to pass `ps_conn` while we are in the
file, otherwise the env-var fallback silently does nothing.

## Known caveat (flagged, not fixed here)

Per [notes/scrapyrus-embeddings.md](notes/scrapyrus-embeddings.md), scrapyrus
writes its own `transcription_embeddings` / `translation_embeddings` tables,
**not** LangChain's `langchain_pg_embedding` / `langchain_pg_collection` schema
that `PGVector` reads. So this retriever will find nothing against a
scrapyrus-populated database until either the data is re-ingested through
`PGVector`, or `RetrievalAgent` is given a custom retriever over the scrapyrus
tables. The formatting/plumbing work above is independent of which way that
goes; the metadata keys the formatter looks for (`tm_id`, `source_path`,
`chunk_index`, `language`) are the scrapyrus column names either way.

## Verification

1. Unit-test the formatter with fabricated `Document` objects — no DB needed:
   documents with full metadata, with empty metadata, and an empty list.
   `backend/tests/` currently references a removed `chat_langchain` module, so
   add a fresh `test_retrieval_agent.py` rather than extending the stale files.
2. Fake-agent test of the contract: monkeypatch `agent` in `chat.py` with a stub
   whose `retrieve` returns the dict, set `MODE = "retrieval"`, and assert
   `answer_with_chat` output validates against `server.ChatResponse`.
3. End to end, with Postgres up (`docker compose up postgres`) and an embedding
   model reachable:
   - `POST /changemode?mode=retrieval`, then `POST /new`, then `POST /chat` with
     `{"messages": [{"content": [{"text": "tax receipt Oxyrhynchus"}]}]}`.
   - Expect a 200 whose `text` is the markdown hit list and whose `reasoning` is
     `""` and `interrupt` is `null`.
4. In the browser, confirm the hit list renders as headings/blockquotes rather
   than raw markdown.
