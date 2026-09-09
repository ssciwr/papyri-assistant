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


def test_discovery_requires_three_current_complete_rows():
    result = module.discover_specifications(cast(Any, Connection(metadata_rows())))
    assert set(result) == set(CORPUS_MAPPINGS)
    assert result["keywords"].table_name == "keyword_embeddings"
    assert result["translations"].provider_options == {
        "check_embedding_ctx_length": False
    }

    cases = [
        (metadata_rows()[:-1], "Missing embedding metadata"),
        ([(*metadata_rows()[0][:2], None, *metadata_rows()[0][3:])], "dimension"),
        ([(*metadata_rows()[0][:3], None, *metadata_rows()[0][4:])], "provider"),
        ([(*metadata_rows()[0][:4], [], *metadata_rows()[0][5:])], "provider_options"),
        ([(*metadata_rows()[0][:3], "unknown", *metadata_rows()[0][4:])], "unsupported embedding provider"),
        ([(*metadata_rows()[0][:6], 9)], "contract version"),
    ]
    for rows, message in cases:
        with pytest.raises(EmbeddingContractError, match=message):
            module.discover_specifications(cast(Any, Connection(rows)))


def test_discovery_wraps_database_errors_and_rolls_back():
    connection = Connection([], RuntimeError("missing table"))
    with pytest.raises(EmbeddingContractError, match="current Scrapyrus"):
        module.discover_specifications(cast(Any, connection))
    assert connection.rollback_calls == 1


def test_specification_identity_covers_compatibility_not_table_or_size():
    first = specification()
    same = replace(first, table_name="other", embedding_size=99)
    assert first.identity == same.identity
    assert first.identity != replace(first, provider_options={}).identity


def test_endpoint_profile_and_provider_credentials(monkeypatch):
    monkeypatch.delenv("EMBEDDING_ENDPOINT_LOCAL", raising=False)
    with pytest.raises(EmbeddingContractError, match="EMBEDDING_ENDPOINT_LOCAL"):
        module._endpoint(specification())
    monkeypatch.setenv("EMBEDDING_ENDPOINT_LOCAL", "http://embed/v1")
    assert module._endpoint(specification()) == "http://embed/v1"
    assert module._endpoint(specification(endpoint_profile=None)) is None
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(EmbeddingContractError, match="OPENAI_API_KEY"):
        module._secret("openai")
    monkeypatch.delenv("VLLM_API_KEY", raising=False)
    assert module._secret("vllm") == "EMPTY"
    assert module._secret("huggingface") is None


def test_openai_and_voyage_factories_use_allowlisted_options(monkeypatch):
    monkeypatch.setenv("EMBEDDING_ENDPOINT_LOCAL", "http://embed/v1")
    monkeypatch.setenv("VLLM_API_KEY", "key")
    openai = module.build_embeddings(specification())
    assert openai.model == "model-a"
    assert str(openai.openai_api_base) == "http://embed/v1"

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

    with pytest.raises(EmbeddingContractError, match="unsupported"):
        module.build_embeddings(specification(provider_options={"surprise": True}))
    with pytest.raises(EmbeddingContractError, match="unsupported embedding provider"):
        module.build_embeddings(
            specification(provider="unknown", endpoint_profile=None)
        )


def test_table_validation_selects_dimension_appropriate_column():
    mapping = CORPUS_MAPPINGS["transcriptions"]
    basic = [
        (name, "text")
        for name in {
            mapping.id_column,
            mapping.content_column,
            *mapping.metadata_columns,
        }
    ]
    connection = Connection([*basic, ("embedding", "vector(2)")])
    assert module._validate_table(cast(Any, connection), mapping, specification()) == (
        "embedding"
    )

    high = specification(embedding_size=2560)
    connection = Connection([*basic, ("search_embedding", "halfvec(2560)")])
    assert module._validate_table(cast(Any, connection), mapping, high) == (
        "search_embedding"
    )

    with pytest.raises(EmbeddingContractError, match="missing required columns"):
        module._validate_table(cast(Any, Connection([])), mapping, specification())
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

    def similarity_search_by_vector(self, value, **kwargs):
        self.calls.append(("similarity-vector", value, kwargs))
        return self.documents

    def max_marginal_relevance_search_by_vector(self, value, **kwargs):
        self.calls.append(("mmr-vector", value, kwargs))
        return self.documents


def test_retriever_forwards_searches_and_validates_vector_provenance():
    store = RecordingStore()
    retriever = LangChainRetriever(
        corpus="transcriptions",
        specification=specification(),
        embeddings=cast(Any, object()),
        store=cast(Any, store),
        similarity_search_kwargs={"k": 2},
        mmr_search_kwargs={"k": 3, "fetch_k": 8},
    )
    assert retriever.similarity_search("lease") is store.documents
    assert retriever.mmr_search("variety") is store.documents
    identity = retriever.specification_id
    assert retriever.similarity_search_by_vec([0.1, 0.2], identity) is store.documents
    assert retriever.mmr_search_by_vec([0.3, 0.4], identity) is store.documents
    assert [call[0] for call in store.calls] == [
        "similarity",
        "mmr",
        "similarity-vector",
        "mmr-vector",
    ]
    with pytest.raises(ValueError, match="provenance"):
        retriever.similarity_search_by_vec([0.1, 0.2], "wrong")
    with pytest.raises(ValueError, match="dimensions"):
        retriever.mmr_search_by_vec([0.1], identity)


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
    monkeypatch.setattr(
        module.PGEngine, "from_connection_string", lambda _url: engine
    )

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


def test_build_retrievers_rejects_missing_url_bad_probe_and_closes(monkeypatch):
    monkeypatch.delenv("POSTGRES_URL", raising=False)
    with pytest.raises(EmbeddingContractError, match="POSTGRES_URL"):
        module.build_retrievers(cast(Any, object()))

    engine = ClosingEngine()
    specs = {
        corpus: specification(table_name=mapping.table_name)
        for corpus, mapping in CORPUS_MAPPINGS.items()
    }
    monkeypatch.setenv("POSTGRES_URL", "postgresql://reader@db/papyri")
    monkeypatch.setattr(module, "discover_specifications", lambda _connection: specs)
    monkeypatch.setattr(module, "_validate_table", lambda *_args: "embedding")
    monkeypatch.setattr(module, "build_embeddings", lambda _spec: FakeEmbeddings(3))
    monkeypatch.setattr(
        module.PGEngine, "from_connection_string", lambda _url: engine
    )
    with pytest.raises(EmbeddingContractError, match="provider returned 3"):
        module.build_retrievers(cast(Any, object()))
    assert engine.close_calls == 1
