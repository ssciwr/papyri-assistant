"""Unit coverage for the PGVectorStore retrieval adapter."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import ANY

import pytest

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


class FakeStore:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any, dict[str, Any]]] = []

    def similarity_search(self, query: str, **kwargs: Any) -> list[str]:
        self.calls.append(("similarity", query, kwargs))
        return ["similar"]


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch) -> FakeStore:
    store = FakeStore()
    create_calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    monkeypatch.setenv("POSTGRES_URL", "postgresql://test")
    monkeypatch.setattr(
        retrieval_module,
        "PGEngine",
        SimpleNamespace(from_connection_string=lambda _: "vector-engine"),
    )
    monkeypatch.setattr(
        retrieval_module,
        "PGVectorStore",
        SimpleNamespace(
            create_sync=lambda *args, **kwargs: create_calls.append((args, kwargs))
            or store
        ),
    )
    store.create_calls = create_calls
    return store


def test_opens_the_configured_table(store: FakeStore) -> None:
    LangChainRetriever(embeddings=object(), store_kwargs=STORE_KWARGS)

    args, kwargs = store.create_calls[0]
    assert args == ("vector-engine", ANY, "embeddings")
    assert kwargs == {
        "schema_name": "public",
        "content_column": "content",
        "embedding_column": "embedding",
        "id_column": "chunk_id",
        "metadata_columns": ["source", "transcription_id"],
        "metadata_json_column": "metadata",
    }


def test_similarity_search_uses_the_configured_arguments(store: FakeStore) -> None:
    retriever = LangChainRetriever(
        embeddings=object(),
        store_kwargs=STORE_KWARGS,
        similarity_search_kwargs={"k": 2},
    )

    assert retriever.similarity_search("papyrus") == ["similar"]
    assert store.calls == [("similarity", "papyrus", {"k": 2})]


def test_missing_table_settings_raise_value_error(store: FakeStore) -> None:
    with pytest.raises(ValueError, match="store_kwargs"):
        LangChainRetriever(embeddings=object(), store_kwargs={})
