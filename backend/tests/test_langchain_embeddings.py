"""Behavioral coverage for the PGVectorStore embedding adapter."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import yaml
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

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


class RecordingVectorEngine:
    """Record table creation at the unavailable PGEngine boundary."""

    def __init__(self) -> None:
        self.initializations: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def init_vectorstore_table(self, *args: Any, **kwargs: Any) -> None:
        self.initializations.append((args, kwargs))


class RecordingStore:
    """Record documents sent to the unavailable pgvector persistence boundary."""

    def __init__(self) -> None:
        self.add_calls: list[tuple[list[Any], list[str]]] = []

    def add_documents(self, documents: list[Any], *, ids: list[str]) -> list[str]:
        self.add_calls.append((documents, ids))
        return ids


@dataclass
class RecordingPgvector:
    """Typed recording replacement for the external pgvector services."""

    vector_engine: RecordingVectorEngine = field(default_factory=RecordingVectorEngine)
    vector_urls: list[Any] = field(default_factory=list)
    stores: list[RecordingStore] = field(default_factory=list)
    store_create_calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = field(
        default_factory=list
    )
    table_exists: bool = False

    def open_vector_engine(self, url: Any) -> RecordingVectorEngine:
        self.vector_urls.append(url)
        return self.vector_engine

    def open_store(self, *args: Any, **kwargs: Any) -> RecordingStore:
        self.store_create_calls.append((args, kwargs))
        store = RecordingStore()
        self.stores.append(store)
        return store

    def has_table(self, table_name: str, schema: str) -> bool:
        return self.table_exists


@pytest.fixture
def recording_pgvector(monkeypatch: pytest.MonkeyPatch) -> RecordingPgvector:
    backend = RecordingPgvector()
    monkeypatch.setenv("POSTGRES_URL", "postgresql://writer:secret@db.example/papyri")
    monkeypatch.setattr(embeddings_module, "inspect", lambda _: backend)
    monkeypatch.setattr(
        embeddings_module,
        "PGEngine",
        SimpleNamespace(from_connection_string=backend.open_vector_engine),
    )
    monkeypatch.setattr(
        embeddings_module,
        "PGVectorStore",
        SimpleNamespace(create_sync=backend.open_store),
    )
    return backend


@pytest.fixture
def sqlite_source_engine() -> Iterator[Callable[[list[dict[str, Any]]], Engine]]:
    sqlite3.register_converter("JSON", lambda value: json.loads(value.decode()))
    engines: list[Engine] = []

    def create(rows: list[dict[str, Any]]) -> Engine:
        engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"detect_types": sqlite3.PARSE_DECLTYPES},
        )
        engines.append(engine)
        with engine.begin() as connection:
            connection.exec_driver_sql(
                """
                CREATE TABLE source_documents (
                    transcription_id INTEGER,
                    source_path TEXT,
                    tm_id INTEGER,
                    type TEXT,
                    language TEXT,
                    text TEXT,
                    dates JSON,
                    places JSON
                )
                """
            )
            for row in rows:
                connection.execute(
                    text(
                        """
                        INSERT INTO source_documents VALUES (
                            :transcription_id, :source_path, :tm_id, :type,
                            :language, :text, :dates, :places
                        )
                        """
                    ),
                    {
                        **row,
                        "dates": json.dumps(row["dates"]),
                        "places": json.dumps(row["places"]),
                    },
                )
        return engine

    yield create

    for engine in engines:
        engine.dispose()


def build_embedder(
    recording_pgvector: RecordingPgvector, *, chunk_size: int = 1000
) -> LangChainEmbeddings:
    recording_pgvector.table_exists = True
    return LangChainEmbeddings(
        embeddings=object(),
        splitter_kwargs={"chunk_size": chunk_size, "chunk_overlap": 0},
        store_kwargs=STORE_KWARGS,
    )


def test_initialization_uses_real_engine_url_and_creates_a_missing_table(
    recording_pgvector: RecordingPgvector,
) -> None:
    embeddings = object()

    embedder = LangChainEmbeddings(
        embeddings=embeddings,
        store_kwargs=STORE_KWARGS,
    )

    assert embedder.engine.url.drivername == "postgresql+psycopg"
    assert embedder.engine.url.username == "writer"
    assert embedder.engine.url.database == "papyri"
    assert recording_pgvector.vector_urls[0].drivername == "postgresql+psycopg"

    args, kwargs = recording_pgvector.vector_engine.initializations[0]
    assert args == ("embeddings", 2000)
    assert kwargs["overwrite_existing"] is False
    assert kwargs["id_column"].name == "chunk_id"
    assert kwargs["id_column"].data_type == "TEXT"
    assert [column.name for column in kwargs["metadata_columns"]] == [
        "source",
        "transcription_id",
    ]

    store_args, store_kwargs = recording_pgvector.store_create_calls[0]
    assert store_args == (recording_pgvector.vector_engine, embeddings, "embeddings")
    assert store_kwargs["id_column"] == "chunk_id"
    assert store_kwargs["metadata_columns"] == ["source", "transcription_id"]


def test_initialization_opens_an_existing_table_without_recreating_it(
    recording_pgvector: RecordingPgvector,
) -> None:
    recording_pgvector.table_exists = True

    LangChainEmbeddings(embeddings=object(), store_kwargs=STORE_KWARGS)

    assert recording_pgvector.vector_engine.initializations == []
    assert len(recording_pgvector.stores) == 1


def test_reset_replaces_the_table_with_the_configured_schema(
    recording_pgvector: RecordingPgvector,
) -> None:
    embedder = build_embedder(recording_pgvector)

    embedder.reset_everything()

    args, kwargs = recording_pgvector.vector_engine.initializations[0]
    assert args == ("embeddings", 2000)
    assert kwargs["overwrite_existing"] is True
    assert len(recording_pgvector.stores) == 2
    assert embedder.store is recording_pgvector.stores[-1]


def test_missing_database_url_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("POSTGRES_URL", raising=False)

    with pytest.raises(ValueError, match="POSTGRES_URL"):
        LangChainEmbeddings(embeddings=object(), store_kwargs=STORE_KWARGS)


@pytest.mark.parametrize(
    ("store_kwargs", "message"),
    [
        (None, "must be a mapping"),
        ({"table_name": "embeddings"}, "missing: .*vector_size"),
        (
            {**STORE_KWARGS, "id_column": {"name": "chunk_id"}},
            "column is missing: data_type, nullable",
        ),
        (
            {
                **STORE_KWARGS,
                "metadata_columns": [{"name": "source", "nullable": False}],
            },
            "column is missing: data_type",
        ),
    ],
)
def test_malformed_table_contracts_are_rejected(
    store_kwargs: Any, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        LangChainEmbeddings(embeddings=object(), store_kwargs=store_kwargs)


def test_from_config_uses_real_yaml_loading_building_and_splitter(
    tmp_path: Path,
    recording_pgvector: RecordingPgvector,
) -> None:
    recording_pgvector.table_exists = True
    config = tmp_path / "embedder.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "embeddings": {
                    "type": "types.SimpleNamespace",
                    "kwargs": {"name": "configured-embeddings"},
                },
                "splitter_kwargs": {"chunk_size": 4, "chunk_overlap": 0},
                "store_kwargs": STORE_KWARGS,
            }
        )
    )

    embedder = LangChainEmbeddings.from_config(config)
    embedder.compute_document_embeddings(
        "abcdefgh", {"transcription_id": "42"}, source="configured"
    )

    documents, ids = recording_pgvector.stores[0].add_calls[0]
    assert embedder.embeddings.name == "configured-embeddings"
    assert [document.page_content for document in documents] == ["abcd", "efgh"]
    assert ids == ["configured:42:0", "configured:42:1"]


def test_document_chunks_retain_all_papyrus_metadata(
    recording_pgvector: RecordingPgvector,
    papyrus_record: dict[str, Any],
    papyrus_metadata: dict[str, Any],
) -> None:
    embedder = build_embedder(recording_pgvector, chunk_size=12)
    metadata = {
        **papyrus_metadata,
        "transcription_id": str(papyrus_metadata["transcription_id"]),
    }

    embedder.compute_document_embeddings(
        papyrus_record["transcription"], metadata, source="synthetic-fixture"
    )

    documents, ids = recording_pgvector.stores[0].add_calls[0]
    assert len(documents) > 1
    assert all(document.metadata == metadata for document in documents)
    assert [document.metadata["dates"] for document in documents] == [
        papyrus_record["dates"]
    ] * len(documents)
    assert [document.metadata["places"] for document in documents] == [
        papyrus_record["places"]
    ] * len(documents)
    assert ids == [
        f"synthetic-fixture:{papyrus_record['transcription_id']}:{index}"
        for index in range(len(documents))
    ]


def test_embedd_selection_uses_real_sqlalchemy_and_preserves_row_metadata(
    recording_pgvector: RecordingPgvector,
    papyrus_row: dict[str, Any],
    sqlite_source_engine: Callable[[list[dict[str, Any]]], Engine],
) -> None:
    second_row = {
        **papyrus_row,
        "transcription_id": 790,
        "source_path": "P.Oxy./P.Oxy.12.1451.xml",
        "tm_id": 123457,
        "text": "Short receipt",
        "dates": [],
        "places": [],
    }
    embedder = build_embedder(recording_pgvector)
    source_engine = sqlite_source_engine([papyrus_row, second_row])
    embedder.engine = source_engine

    selection = """
        SELECT transcription_id, source_path, tm_id, type, language,
               text, dates, places
        FROM source_documents
        ORDER BY transcription_id;
        """.strip()
    count = embedder.embedd_selection(selection, source="unit-corpus")

    assert count == 2
    add_calls = recording_pgvector.stores[0].add_calls
    assert len(add_calls) == 2
    first_document, second_document = add_calls[0][0][0], add_calls[1][0][0]
    assert first_document.metadata == {
        "source": "unit-corpus",
        "transcription_id": str(papyrus_row["transcription_id"]),
        "source_path": papyrus_row["source_path"],
        "tm_id": papyrus_row["tm_id"],
        "document_type": papyrus_row["type"],
        "language": papyrus_row["language"],
        "dates": papyrus_row["dates"],
        "places": papyrus_row["places"],
    }
    assert second_document.metadata["dates"] == []
    assert second_document.metadata["places"] == []
    assert add_calls[0][1] == [f"unit-corpus:{papyrus_row['transcription_id']}:0"]
    assert add_calls[1][1] == ["unit-corpus:790:0"]


def test_embedd_selection_handles_an_empty_real_query_result(
    recording_pgvector: RecordingPgvector,
    sqlite_source_engine: Callable[[list[dict[str, Any]]], Engine],
) -> None:
    embedder = build_embedder(recording_pgvector)
    source_engine = sqlite_source_engine([])
    embedder.engine = source_engine

    count = embedder.embedd_selection(
        """
        SELECT transcription_id, source_path, tm_id, type, language,
               text, dates, places
        FROM source_documents
        """
    )

    assert count == 0
    assert recording_pgvector.stores[0].add_calls == []


def test_embedd_everything_defines_the_postgres_selection_contract(
    monkeypatch: pytest.MonkeyPatch,
    recording_pgvector: RecordingPgvector,
) -> None:
    embedder = build_embedder(recording_pgvector)
    captured: dict[str, Any] = {}

    def capture(query: str, source: str) -> int:
        captured.update(query=query, source=source)
        return 7

    monkeypatch.setattr(embedder, "embedd_selection", capture)

    result = embedder.embedd_everything(source="complete-corpus")

    assert result == 7
    assert captured["source"] == "complete-corpus"
    assert "jsonb_agg" in captured["query"]
    assert "COALESCE(dates.values, '[]'::jsonb)" in captured["query"]
    assert "COALESCE(places.values, '[]'::jsonb)" in captured["query"]
    assert "WHERE text <> ''" in captured["query"]
