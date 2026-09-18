"""Real PostgreSQL/pgvector proof of the published Scrapyrus mappings."""

from __future__ import annotations

import os

from langchain_core.embeddings import Embeddings
import psycopg
import pytest

from papyri_backend import langchain_retrieval


pytestmark = pytest.mark.integration


class DeterministicEmbeddings(Embeddings):
    def __init__(self, dimensions: int):
        self.dimensions = dimensions

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        vector[0 if "first" in text or "alpha" in text else 1] = 1.0
        return vector


def _literal(dimensions: int, index: int) -> str:
    values = ["0"] * dimensions
    values[index] = "1"
    return f"[{','.join(values)}]"


def test_real_pgvector_similarity_mmr_and_keyword_mapping(monkeypatch):
    database_url = os.environ["POSTGRES_URL"]
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE transcription_embeddings, translation_embeddings, keyword_embeddings, embedding_table_metadata")
            for table in ("transcription_embeddings", "keyword_embeddings"):
                cursor.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS search_embedding")
                cursor.execute(f"ALTER TABLE {table} ALTER COLUMN embedding TYPE vector(2) USING embedding::vector(2)")
            cursor.execute("ALTER TABLE translation_embeddings DROP COLUMN IF EXISTS search_embedding")
            cursor.execute("ALTER TABLE translation_embeddings ALTER COLUMN embedding TYPE vector(2560) USING embedding::vector(2560)")
            cursor.execute("ALTER TABLE translation_embeddings ADD COLUMN search_embedding halfvec(2560) GENERATED ALWAYS AS (embedding::halfvec(2560)) STORED")
            cursor.executemany(
                "INSERT INTO embedding_table_metadata (table_name, model_name, embedding_size, provider, provider_options, endpoint_profile, contract_version) VALUES (%s, %s, %s, 'vllm', '{\"check_embedding_ctx_length\": false}', 'fixture', 1)",
                [
                    ("transcription_embeddings", "small", 2),
                    ("translation_embeddings", "large", 2560),
                    ("keyword_embeddings", "small", 2),
                ],
            )
            cursor.executemany(
                "INSERT INTO transcription_embeddings (chunk_id, xml_id, chunk_index, source_path, tm_id, language, document_text, input_hash, embedding) VALUES (%s, 1, %s, 'a.xml', '1', 'grc', %s, 'hash', %s::vector)",
                [
                    ("transcriptions:1:0", 0, "alpha first chunk", "[1,0]"),
                    ("transcriptions:1:1", 1, "beta second chunk", "[0,1]"),
                ],
            )
            cursor.executemany(
                "INSERT INTO translation_embeddings (chunk_id, xml_id, chunk_index, source_path, tm_id, language, document_text, input_hash, embedding) VALUES (%s, 2, %s, 'b.xml', '2', 'en', %s, 'hash', %s::vector)",
                [
                    ("translations:2:0", 0, "first translation", _literal(2560, 0)),
                    ("translations:2:1", 1, "second translation", _literal(2560, 1)),
                ],
            )
            cursor.executemany(
                "INSERT INTO keyword_embeddings (keyword, embedding) VALUES (%s, %s::vector)",
                [("alpha", "[1,0]"), ("beta, private", "[0,1]")],
            )
        connection.commit()

        monkeypatch.setenv("POSTGRES_URL", database_url)
        monkeypatch.setattr(
            langchain_retrieval,
            "build_embeddings",
            lambda spec: DeterministicEmbeddings(spec.embedding_size),
        )
        retrievers, engine = langchain_retrieval.build_retrievers(connection)
        try:
            transcription = retrievers["transcriptions"]
            chunks = transcription.similarity_search("alpha first")
            assert chunks[0].id == "transcriptions:1:0"
            assert chunks[0].metadata["chunk_index"] == 0
            assert transcription.mmr_search("alpha first")
            assert retrievers["keywords"].similarity_search("alpha")[0].id == "alpha"
            assert retrievers["translations"].similarity_search("first")[0].id == "translations:2:0"
            assert retrievers["translations"].mmr_search("first")
        finally:
            langchain_retrieval.close_vector_engine(engine)
