"""Unit coverage for the PGVectorStore embedding adapter."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from papyri_backend import langchain_embeddings as embeddings_module
from papyri_backend.langchain_embeddings import LangChainEmbeddings


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


class FakeVectorEngine:
    def __init__(self) -> None:
        self.initializations: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def init_vectorstore_table(self, *args: Any, **kwargs: Any) -> None:
        self.initializations.append((args, kwargs))


class FakeStore:
    def __init__(self) -> None:
        self.add_calls: list[tuple[list[Any], list[str]]] = []

    def add_documents(self, documents: list[Any], *, ids: list[str]) -> list[str]:
        self.add_calls.append((documents, ids))
        return ids


@pytest.fixture
def adapter_dependencies(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    vector_engine = FakeVectorEngine()
    stores: list[FakeStore] = []
    inspected = SimpleNamespace(exists=False)

    monkeypatch.setenv("POSTGRES_URL", "postgresql://test")
    monkeypatch.setattr(embeddings_module, "create_engine", lambda _: object())
    monkeypatch.setattr(
        embeddings_module,
        "inspect",
        lambda _: SimpleNamespace(
            has_table=lambda table_name, schema: inspected.exists
        ),
    )
    monkeypatch.setattr(
        embeddings_module,
        "PGEngine",
        SimpleNamespace(from_connection_string=lambda _: vector_engine),
    )

    def create_sync(*_: Any, **__: Any) -> FakeStore:
        store = FakeStore()
        stores.append(store)
        return store

    monkeypatch.setattr(
        embeddings_module,
        "PGVectorStore",
        SimpleNamespace(create_sync=create_sync),
    )
    return SimpleNamespace(
        vector_engine=vector_engine,
        stores=stores,
        inspected=inspected,
    )


def test_initialization_creates_only_a_missing_table(adapter_dependencies) -> None:
    LangChainEmbeddings(embeddings=object(), store_kwargs=STORE_KWARGS)

    assert len(adapter_dependencies.vector_engine.initializations) == 1
    args, kwargs = adapter_dependencies.vector_engine.initializations[0]
    assert args == ("embeddings", 2000)
    assert kwargs["overwrite_existing"] is False
    assert kwargs["id_column"].name == "chunk_id"
    assert kwargs["id_column"].data_type == "TEXT"
    assert [column.name for column in kwargs["metadata_columns"]] == [
        "source",
        "transcription_id",
    ]


def test_initialization_opens_an_existing_table_without_recreating_it(
    adapter_dependencies,
) -> None:
    adapter_dependencies.inspected.exists = True

    LangChainEmbeddings(embeddings=object(), store_kwargs=STORE_KWARGS)

    assert adapter_dependencies.vector_engine.initializations == []
    assert len(adapter_dependencies.stores) == 1


def test_reset_replaces_the_table_with_the_configured_schema(
    adapter_dependencies,
) -> None:
    adapter_dependencies.inspected.exists = True
    embedder = LangChainEmbeddings(embeddings=object(), store_kwargs=STORE_KWARGS)

    embedder.reset_everything()

    args, kwargs = adapter_dependencies.vector_engine.initializations[0]
    assert args == ("embeddings", 2000)
    assert kwargs["overwrite_existing"] is True
    assert len(adapter_dependencies.stores) == 2


def test_document_chunks_use_stable_source_coordinates(adapter_dependencies) -> None:
    adapter_dependencies.inspected.exists = True
    embedder = LangChainEmbeddings(
        embeddings=object(),
        splitter_kwargs={"chunk_size": 4, "chunk_overlap": 0},
        store_kwargs=STORE_KWARGS,
    )

    embedder.compute_document_embeddings(
        "abcdefgh",
        {"source": "scrapyrus", "transcription_id": "42"},
    )

    documents, ids = adapter_dependencies.stores[0].add_calls[0]
    assert [document.page_content for document in documents] == ["abcd", "efgh"]
    assert ids == ["scrapyrus:42:0", "scrapyrus:42:1"]


def test_initialization_rejects_an_incomplete_table_contract(
    adapter_dependencies,
) -> None:
    with pytest.raises(ValueError, match="missing: .*vector_size"):
        LangChainEmbeddings(
            embeddings=object(),
            store_kwargs={"table_name": "embeddings"},
        )
