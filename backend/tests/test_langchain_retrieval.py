"""Database-contract and routing tests for the three retrieval corpora."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, cast

from langchain_core.documents import Document
import pytest

from papyri_backend import langchain_retrieval as module
from papyri_backend.langchain_retrieval import (
    CORPUS_MAPPINGS,
    EmbeddingContractError,
    EmbeddingSpecification,
    LangChainRetriever,
)


def specification(**changes: Any) -> EmbeddingSpecification:
    value = EmbeddingSpecification(
        table_name="transcription_embeddings",
        model_name="model-a",
        embedding_size=2,
        provider="vllm",
        provider_options={"check_embedding_ctx_length": False},
        endpoint_profile="local",
        contract_version=1,
    )
    return replace(value, **changes)


class Cursor:
    def __init__(self, rows: list[Any], error: Exception | None = None):
        self.rows = rows
        self.error = error
        self.executions: list[tuple[Any, Any]] = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, query, params=None):
        self.executions.append((query, params))
        if self.error:
            raise self.error

    def fetchall(self):
        return self.rows


class Connection:
    def __init__(self, rows: list[Any], error: Exception | None = None):
        self.cursor_value = Cursor(rows, error)
        self.rollback_calls = 0

    def cursor(self):
        return self.cursor_value

    def rollback(self):
        self.rollback_calls += 1


def metadata_rows():
    return [
        (
            mapping.table_name,
            f"model-{corpus}",
            2,
            "vllm",
            {"check_embedding_ctx_length": False},
            "local",
            1,
        )
        for corpus, mapping in CORPUS_MAPPINGS.items()
    ]


@pytest.mark.parametrize(
    ("rows", "message"),
    [
        pytest.param(
            metadata_rows()[:-1], "Missing embedding metadata", id="missing-corpus"
        ),
        pytest.param(
            [(*metadata_rows()[0][:2], None, *metadata_rows()[0][3:])],
            "dimension",
            id="missing-dimension",
        ),
        pytest.param(
            [(*metadata_rows()[0][:3], None, *metadata_rows()[0][4:])],
            "provider",
            id="missing-provider",
        ),
        pytest.param(
            [(*metadata_rows()[0][:4], [], *metadata_rows()[0][5:])],
            "provider_options",
            id="invalid-provider-options",
        ),
        pytest.param(
            [(*metadata_rows()[0][:3], "unknown", *metadata_rows()[0][4:])],
            "unsupported embedding provider",
            id="unsupported-provider",
        ),
        pytest.param(
            [(*metadata_rows()[0][:6], 9)],
            "contract version",
            id="wrong-contract-version",
        ),
    ],
)
def test_discovery_rejects_invalid_metadata(rows, message):
    with pytest.raises(EmbeddingContractError, match=message):
        module.discover_specifications(cast(Any, Connection(rows)))


def test_discovery_wraps_database_errors_and_rolls_back():
    connection = Connection([], RuntimeError("missing table"))
    with pytest.raises(EmbeddingContractError, match="current Scrapyrus"):
        module.discover_specifications(cast(Any, connection))
    assert connection.rollback_calls == 1


def test_endpoint_requires_a_configured_profile(monkeypatch):
    monkeypatch.delenv("EMBEDDING_ENDPOINT_LOCAL", raising=False)

    with pytest.raises(EmbeddingContractError, match="EMBEDDING_ENDPOINT_LOCAL"):
        module._endpoint(specification())


@pytest.mark.parametrize(
    ("profile", "expected"),
    [("local", "http://embed/v1"), (None, None)],
)
def test_endpoint_resolves_an_optional_profile(monkeypatch, profile, expected):
    monkeypatch.setenv("EMBEDDING_ENDPOINT_LOCAL", "http://embed/v1")

    assert module._endpoint(specification(endpoint_profile=profile)) == expected


def test_openai_secret_requires_an_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(EmbeddingContractError, match="OPENAI_API_KEY"):
        module._secret("openai")


def test_vllm_secret_defaults_to_a_non_secret_placeholder(monkeypatch):
    monkeypatch.delenv("VLLM_API_KEY", raising=False)

    vllm_secret = module._secret("vllm")

    assert vllm_secret is not None
    assert vllm_secret.get_secret_value() == "EMPTY"


def test_a_provider_without_credentials_has_no_secret():
    assert module._secret("huggingface") is None


def test_openai_compatible_factory_uses_configured_options(monkeypatch):
    monkeypatch.setenv("EMBEDDING_ENDPOINT_LOCAL", "http://embed/v1")
    monkeypatch.setenv("VLLM_API_KEY", "key")

    openai = module.build_embeddings(specification())

    assert openai.model == "model-a"
    assert str(openai.openai_api_base) == "http://embed/v1"


def test_voyage_factory_uses_allowlisted_options(monkeypatch):
    monkeypatch.setenv("VOYAGE_API_KEY", "key")

    voyage = module.build_embeddings(
        specification(
            provider="voyageai",
            endpoint_profile=None,
            provider_options={
                "output_dimension": 1024,
                "truncation": False,
                "batch_size": 64,
                "document_input_type": "document",
                "query_input_type": "query",
            },
        )
    )
    assert voyage.output_dimension == 1024
    assert voyage.truncation is False


def test_embedding_factory_rejects_an_unsupported_option(monkeypatch):
    monkeypatch.setenv("EMBEDDING_ENDPOINT_LOCAL", "http://embed/v1")

    with pytest.raises(EmbeddingContractError, match="unsupported"):
        module.build_embeddings(specification(provider_options={"surprise": True}))


def test_embedding_factory_rejects_an_unsupported_provider():
    with pytest.raises(EmbeddingContractError, match="unsupported embedding provider"):
        module.build_embeddings(
            specification(provider="unknown", endpoint_profile=None)
        )


@pytest.mark.parametrize(
    ("embedding_size", "embedding_column", "column_type"),
    [
        pytest.param(2, "embedding", "vector(2)", id="vector"),
        pytest.param(2560, "search_embedding", "halfvec(2560)", id="large-halfvec"),
    ],
)
def test_table_validation_selects_dimension_appropriate_column(
    embedding_size, embedding_column, column_type
):
    mapping = CORPUS_MAPPINGS["transcriptions"]
    basic = [
        (name, "text")
        for name in {
            mapping.id_column,
            mapping.content_column,
            *mapping.metadata_columns,
        }
    ]
    connection = Connection([*basic, (embedding_column, column_type)])

    assert (
        module._validate_table(
            cast(Any, connection), mapping, specification(embedding_size=embedding_size)
        )
        == embedding_column
    )


def test_table_validation_rejects_missing_required_columns():
    mapping = CORPUS_MAPPINGS["transcriptions"]

    with pytest.raises(EmbeddingContractError, match="missing required columns"):
        module._validate_table(cast(Any, Connection([])), mapping, specification())


def test_table_validation_rejects_the_wrong_embedding_type():
    mapping = CORPUS_MAPPINGS["transcriptions"]
    basic = [
        (name, "text")
        for name in {
            mapping.id_column,
            mapping.content_column,
            *mapping.metadata_columns,
        }
    ]

    with pytest.raises(EmbeddingContractError, match=r"expected 'vector\(2\)'"):
        module._validate_table(
            cast(Any, Connection([*basic, ("embedding", "vector")])),
            mapping,
            specification(),
        )


class RecordingStore:
    def __init__(self):
        self.documents = [Document(page_content="chunk")]
        self.calls = []

    def similarity_search(self, value, **kwargs):
        self.calls.append(("similarity", value, kwargs))
        return self.documents

    def max_marginal_relevance_search(self, value, **kwargs):
        self.calls.append(("mmr", value, kwargs))
        return self.documents


@pytest.mark.parametrize(
    ("method", "query", "expected_call"),
    [
        pytest.param(
            "similarity_search",
            "lease",
            ("similarity", "lease", {"k": 2}),
            id="similarity",
        ),
        pytest.param(
            "mmr_search",
            "variety",
            ("mmr", "variety", {"k": 3, "fetch_k": 8}),
            id="mmr",
        ),
    ],
)
def test_retriever_forwards_searches(method, query, expected_call):
    store = RecordingStore()
    retriever = LangChainRetriever(
        store=cast(Any, store),
        similarity_search_kwargs={"k": 2},
        mmr_search_kwargs={"k": 3, "fetch_k": 8},
    )

    result = getattr(retriever, method)(query)

    assert result is store.documents
    assert store.calls == [expected_call]


class FakeEmbeddings:
    def __init__(self, dimensions=2):
        self.dimensions = dimensions
        self.queries = []

    def embed_query(self, query):
        self.queries.append(query)
        return [0.0] * self.dimensions


class ClosingEngine:
    def __init__(self):
        self.close_calls = 0

    def close(self):
        self.close_calls += 1


def test_build_retrievers_shares_engine_and_identical_clients(monkeypatch):
    specs = {
        corpus: specification(table_name=mapping.table_name)
        for corpus, mapping in CORPUS_MAPPINGS.items()
    }
    engine = ClosingEngine()
    stores = []
    clients = []
    monkeypatch.setenv("POSTGRES_URL", "postgresql://reader@db/papyri")
    monkeypatch.setattr(module, "discover_specifications", lambda _connection: specs)
    monkeypatch.setattr(module, "_validate_table", lambda *_args: "embedding")
    monkeypatch.setattr(
        module,
        "build_embeddings",
        lambda _spec: clients.append(FakeEmbeddings()) or clients[-1],
    )
    monkeypatch.setattr(module.PGEngine, "from_connection_string", lambda _url: engine)

    def create(*args, **kwargs):
        stores.append((args, kwargs))
        return RecordingStore()

    monkeypatch.setattr(module.PGVectorStore, "create_sync", create)
    retrievers, result_engine = module.build_retrievers(cast(Any, object()))
    assert set(retrievers) == set(CORPUS_MAPPINGS)
    assert result_engine is engine
    assert len(clients) == 1
    assert len(clients[0].queries) == 1
    assert len(stores) == 3
    assert all(call[1]["metadata_json_column"] is None for call in stores)
    assert all(
        call[1]["distance_strategy"] is module.DistanceStrategy.COSINE_DISTANCE
        for call in stores
    )


def test_build_retrievers_rejects_a_missing_database_url(monkeypatch):
    monkeypatch.delenv("POSTGRES_URL", raising=False)

    with pytest.raises(EmbeddingContractError, match="POSTGRES_URL"):
        module.build_retrievers(cast(Any, object()))


def test_build_retrievers_closes_the_engine_after_a_bad_probe(monkeypatch):
    engine = ClosingEngine()
    specs = {
        corpus: specification(table_name=mapping.table_name)
        for corpus, mapping in CORPUS_MAPPINGS.items()
    }
    monkeypatch.setenv("POSTGRES_URL", "postgresql://reader@db/papyri")
    monkeypatch.setattr(module, "discover_specifications", lambda _connection: specs)
    monkeypatch.setattr(module, "_validate_table", lambda *_args: "embedding")
    monkeypatch.setattr(module, "build_embeddings", lambda _spec: FakeEmbeddings(3))
    monkeypatch.setattr(module.PGEngine, "from_connection_string", lambda _url: engine)
    with pytest.raises(EmbeddingContractError, match="provider returned 3"):
        module.build_retrievers(cast(Any, object()))
    assert engine.close_calls == 1
