# Backend Agent Test-Coverage Plan

## Summary
Build a deterministic, papyrology-oriented test suite around `LangChainAgent` and the code that makes its agentic workflow usable: chat/session lifecycle, FastAPI decision transport, SQL/vector tool adapters, retrieval/embedding adapters, and configuration assembly. Add a separate, opt-in integration lane for the real Postgres/pgvector and configured model stack. Unit tests must never call an LLM, a database, or a vector store.

## Test architecture and interfaces
- Add a shared test-fixture module with:
  - a realistic but synthetic papyrus record (TM identifier, provenance/place, date range, language, transcription, translation, and source/citation metadata);
  - fake streamed model messages, tool-call containers, graph state/interrupts, checkpointer-facing agent, psycopg connection/cursor, retriever/vector store, embeddings, and SQLAlchemy engine;
  - factories for normal user messages and JSON decision replies.
- Add `pytest-cov` to the test extra and configure pytest for branch coverage, `--cov=papyri_backend`, and per-module gates of **90% branch coverage** for `langchain_agent`, `chat`, `session`, `tools/sql`, `tools/pgvec`, `retrieval`, and `embeddings`. Generate terminal-missing-lines and XML reports for CI.
- Register `integration` (requires real dependencies/services) and `live_model` (requires explicitly injected model credentials) markers. The default unit command excludes both markers.

## Unit-test coverage

### Agent adapter (`langchain_agent.py`)
- Test construction and configuration wiring: default in-memory checkpointer, model-first construction/default propagation to nested middleware, supplied checkpointer preservation, generated per-instance thread IDs, and `from_config` delegation.
- Test configuration safety: valid dynamic tool names and filesystem-operation policies; unknown interrupt tool names and unknown permission operations; empty/missing optional configuration; error messages containing invalid and available names.
- Test user-input conversion and protocol parsing: ordinary papyrological research questions (for example, “Which Oxyrhynchus texts mention a lease?”), leading whitespace, slash/backslash wrapper commands, JSON/non-JSON lookalikes, arrays, missing IDs, malformed JSON, and decision JSON with empty decision lists.
- Test event driving using a fake `stream_events(..., version="v3")` implementation: multiple text/reasoning messages, SQL and retrieval tool calls, empty tool-call lists, missing/no event output, graph exceptions, and assertion of payload/config/version passed to the graph.
- Test one-turn state transitions end-to-end with fakes: ordinary question → streamed answer; command rejection without graph execution; run failure replacing partial output; active interrupt appending the decision prompt and rendering an action-specific client view; valid decision → `Command(resume=...)` → resumed output; and refused decisions leaving the pause unmodified.
- Exhaust the resume branches: no pending interrupt, stale interrupt ID, mismatched action/decision counts, action-specific allowed-decision enforcement, approve, edit (forced to paused action name), reject with/without normalized reason, respond with/without a message, and multiple actions whose decisions remain order-preserving.
- Extend output-format tests for tag edge cases and multi-message aggregation: inline and separately emitted reasoning, multiple/stray/whitespace/case-varied think tags, null/empty tool args, absent tool-call names, and error precedence over accumulated answer text.

### Chat, session, and HTTP boundaries
- Cover `chat.answer_with_chat` with empty/malformed message content shapes as the contract is currently consumed, only-last-message behavior, correct propagation of `DecisionError`, ordinary exception recovery, session clearing, and restart behavior.
- Cover `session` with mocked constructors/environment: default versus configured paths, home/relative path handling, missing database URL, successful atomic session construction, constructor failure wrapping and exception chaining, `current` lazy-start/reuse, `clear`, and retriever/connection delegation.
- Use FastAPI `TestClient` for request/response contract tests in addition to direct handler tests: `/health`, `/new`, `/chat` success, agent failure, malformed/empty body, stale decision (409), invalid decision (422), response-model validation, CORS default/configured origins, and no unintended agent initialization for health/validation paths.

### Agent tools and retrieval/embedding adapters
- Unit-test SQL tools with a fake connection: query execution and returned rows, whitespace stripping, table/schema formatting, rollback after success and failure, rollback when fetch fails, and error strings returned rather than raised. Use papyrus tables/columns such as `transcriptions`, `orig_dates`, `orig_places`, `tm_id`, and `source_path` in fixtures.
- Unit-test pgvector tool wrappers by mocking `session.retriever`: each wrapper forwards text/vector input to the correct method and preserves returned document objects and provider failures.
- Test `RetrievalAgent` construction and all four search paths: URL requirement, rejection of caller-provided `connection`, psycopg3 URL normalization, PGVector construction arguments, configured/default kwargs, config loading/building, and exact store method/kwargs forwarding.
- Test `PapyriEmbeddings`: missing URL, URL normalization, config construction, source-document splitting and add-documents call, and `embedd_everything` filtering/counting/mapping. Assert every output chunk retains the synthetic papyrus metadata, including date/place lists and source/transcription IDs; cover empty result sets and rows with empty date/place aggregates.

## Integration and CI lanes
- Create a dedicated backend CI workflow/job (or extend the repository’s existing CI workflow if present) with two explicit jobs:
  - **unit**: install `.[tests]`, run the default marked-excluded suite, enforce branch/module gates, and publish coverage XML;
  - **integration**: provision Postgres with pgvector, apply/load a minimal synthetic papyrology schema and corpus, inject only CI secrets for the configured model endpoint, and run `-m integration`.
- Keep `live_model` tests separate inside the integration job and run them only when model URL/key secrets are available; otherwise report them as skipped, never silently replaced with mocks.
- Integration scenarios will validate: database/vector initialization; an agent research turn that searches the synthetic corpus; SQL schema inspection and a read-only query; an interrupting filesystem action followed by approve and reject responses; and preservation of the thread/checkpoint across a two-turn scholarly query. Assert stable structural outcomes (tool invoked, interrupt protocol, cited fixture identifiers), not model prose.

## Verification and acceptance
- Run the default backend suite from the activated virtual environment with integration/live-model markers excluded; it must have no external network/database dependency and satisfy every module’s 90% branch threshold.
- Run the integration job against a disposable pgvector database; it must cleanly isolate data, prove the synthetic papyrology fixture can traverse SQL and vector paths, and skip live-model cases only when required secrets are absent.
- Review the coverage XML/terminal missing-branch report and add focused tests for every reachable uncovered branch in the named agentic modules; document intentionally unreachable/provider-owned branches with a short justification.

## Assumptions and defaults
- The current public transport contracts (`ChatResponse`, decision JSON with `interrupt_id`, and read-only SQL tools) remain unchanged; this work adds tests and test configuration rather than changing production behavior.
- “Related code” includes the deterministic backend path listed above, while third-party DeepAgents/LangChain internals are mocked in unit tests and exercised only through opt-in integration tests.
- Synthetic papyrology data is committed as minimal test data; no production corpus, credentials, or proprietary document content is used.
- The selected enforcement policy is 90% branch coverage per critical module, and integration is a dedicated CI job with secret-gated live-model tests.
