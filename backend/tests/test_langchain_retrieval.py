"""Behavioral coverage for the PGVectorStore retrieval adapter."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
import yaml
from langchain_core.documents import Document

from papyri_backend import langchain_retrieval as retrieval_module
from papyri_backend.langchain_retrieval import LangChainRetriever


STORE_KWARGS = {
    "table_name": "embeddings",
    "schema_name": "public",
    "vector_size": 2000,
    "content_column": "content",
    "embedding_column": "embedding",
    "id_column": {"name": "chunk_id", "data_type": "TEXT", "nullable": False},
    "metadata_columns": [
        {"name": "source", "data_type": "TEXT", "nullable": False},
        {
            "name": "transcription_id",
            "data_type": "TEXT",
            "nullable": False,
        },
    ],
    "metadata_json_column": "metadata",
}


class RecordingStore:
    """The unavailable pgvector service boundary, with observable calls."""

    def __init__(self) -> None:
        self.documents = [
            Document(
                page_content="Lease of a house from Didyme.",
                metadata={"tm_id": 123456, "transcription_id": "789"},
            )
        ]
        self.calls: list[tuple[str, Any, dict[str, Any]]] = []

    def _record(self, method: str, value: Any, kwargs: dict[str, Any]):
        self.calls.append((method, value, kwargs))
        return self.documents

    def similarity_search(self, query: str, **kwargs: Any):
        return self._record("similarity_search", query, kwargs)

    def max_marginal_relevance_search(self, query: str, **kwargs: Any):
        return self._record("mmr_search", query, kwargs)

    def similarity_search_by_vector(self, vector: list[float], **kwargs: Any):
        return self._record("similarity_search_by_vector", vector, kwargs)

    def max_marginal_relevance_search_by_vector(
        self, vector: list[float], **kwargs: Any
    ):
        return self._record("mmr_search_by_vector", vector, kwargs)


@pytest.fixture
def store_boundary(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    store = RecordingStore()
    engine_urls: list[Any] = []
    create_calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def open_engine(url: Any) -> str:
        engine_urls.append(url)
        return "vector-engine"

    def open_store(*args: Any, **kwargs: Any) -> RecordingStore:
        create_calls.append((args, kwargs))
        return store

    monkeypatch.setenv("POSTGRES_URL", "postgresql://reader:secret@db.example/papyri")
    monkeypatch.setattr(
        retrieval_module,
        "PGEngine",
        SimpleNamespace(from_connection_string=open_engine),
    )
    monkeypatch.setattr(
        retrieval_module,
        "PGVectorStore",
        SimpleNamespace(create_sync=open_store),
    )
    return SimpleNamespace(
        store=store,
        engine_urls=engine_urls,
        create_calls=create_calls,
    )


def test_constructor_normalizes_url_and_opens_the_configured_table(
    store_boundary: SimpleNamespace,
) -> None:
    embeddings = object()

    LangChainRetriever(embeddings=embeddings, store_kwargs=STORE_KWARGS)

    database_url = store_boundary.engine_urls[0]
    assert database_url.drivername == "postgresql+psycopg"
    assert database_url.username == "reader"
    assert database_url.database == "papyri"

    args, kwargs = store_boundary.create_calls[0]
    assert args == ("vector-engine", embeddings, "embeddings")
    assert kwargs == {
        "schema_name": "public",
        "content_column": "content",
        "embedding_column": "embedding",
        "id_column": "chunk_id",
        "metadata_columns": ["source", "transcription_id"],
        "metadata_json_column": "metadata",
    }


def test_missing_database_url_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("POSTGRES_URL", raising=False)

    with pytest.raises(ValueError, match="POSTGRES_URL"):
        LangChainRetriever(embeddings=object(), store_kwargs=STORE_KWARGS)


@pytest.mark.parametrize(
    ("call", "value", "method", "kwargs"),
    [
        ("similarity_search", "papyrus", "similarity_search", {"k": 2}),
        ("mmr_search", "varied papyri", "mmr_search", {"k": 3, "fetch_k": 8}),
        (
            "similarity_search_by_vec",
            [0.1, 0.2],
            "similarity_search_by_vector",
            {"k": 2},
        ),
        (
            "mmr_search_by_vec",
            [0.3, 0.4],
            "mmr_search_by_vector",
            {"k": 3, "fetch_k": 8},
        ),
    ],
)
def test_searches_forward_to_the_matching_store_operation(
    store_boundary: SimpleNamespace,
    call: str,
    value: Any,
    method: str,
    kwargs: dict[str, Any],
) -> None:
    retriever = LangChainRetriever(
        embeddings=object(),
        store_kwargs=STORE_KWARGS,
        similarity_search_kwargs={"k": 2},
        mmr_search_kwargs={"k": 3, "fetch_k": 8},
    )

    result = getattr(retriever, call)(value)

    assert result is store_boundary.store.documents
    assert result[0].metadata["tm_id"] == 123456
    assert store_boundary.store.calls == [(method, value, kwargs)]


def test_searches_default_to_no_extra_store_arguments(
    store_boundary: SimpleNamespace,
) -> None:
    retriever = LangChainRetriever(embeddings=object(), store_kwargs=STORE_KWARGS)

    retriever.similarity_search("papyrus")
    retriever.mmr_search("papyrus")

    assert store_boundary.store.calls == [
        ("similarity_search", "papyrus", {}),
        ("mmr_search", "papyrus", {}),
    ]


def test_from_config_uses_real_yaml_loading_and_object_construction(
    tmp_path: Any,
    store_boundary: SimpleNamespace,
) -> None:
    config = tmp_path / "retriever.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "embeddings": {
                    "type": "types.SimpleNamespace",
                    "kwargs": {"name": "configured-embeddings"},
                },
                "store_kwargs": STORE_KWARGS,
                "similarity_search_kwargs": {"k": 4},
                "mmr_search_kwargs": {"k": 2, "fetch_k": 6},
            }
        )
    )

    retriever = LangChainRetriever.from_config(config)

    assert retriever.embeddings.name == "configured-embeddings"
    assert retriever.similarity_search_kwargs == {"k": 4}
    assert retriever.mmr_search_kwargs == {"k": 2, "fetch_k": 6}


@pytest.mark.parametrize("store_kwargs", [None, {}])
def test_incomplete_table_contract_is_rejected(
    store_boundary: SimpleNamespace, store_kwargs: Any
) -> None:
    with pytest.raises(ValueError, match="store_kwargs"):
        LangChainRetriever(embeddings=object(), store_kwargs=store_kwargs)
