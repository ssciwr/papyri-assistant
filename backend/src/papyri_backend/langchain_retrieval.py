"""Search a pgvector store for the passages the agent's tools ask for."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from langchain_core.documents import Document
from langchain_postgres.v2.engine import PGEngine
from langchain_postgres.v2.vectorstores import PGVectorStore
from sqlalchemy.engine import make_url

from .utils import utils


class LangChainRetriever:
    """Answer questions by searching a PGVectorStore table."""

    @classmethod
    def from_config(cls, path: str | Path) -> LangChainRetriever:
        """Build a retrieval agent from a yaml config file.

        Args:
            path: Path to the config file, whose keys are the arguments below.

        Returns:
            The configured retrieval agent.
        """
        config = utils.load_config(path)
        return cls(embeddings=utils.build(config.pop("embeddings")), **config)

    def __init__(
        self,
        embeddings: Any,
        store_kwargs: dict[str, Any] | None = None,
        similarity_search_kwargs: dict[str, Any] | None = None,
        mmr_search_kwargs: dict[str, Any] | None = None,
    ):
        """Build the vector store the searches run against.

        The database connection is read from the ``POSTGRES_URL`` environment
        variable.

        Args:
            embeddings: The embeddings model queries are embedded with.
            store_kwargs: Table settings shared with ``LangChainEmbeddings``.
            similarity_search_kwargs: Keyword arguments applied to every
                similarity search, such as the number of results ``k``.
            mmr_search_kwargs: Keyword arguments applied to every maximal
                marginal relevance search, such as ``k``.

        Raises:
            ValueError: If ``POSTGRES_URL`` is unset or required table settings
                are missing.
        """
        ps_conn = os.getenv("POSTGRES_URL")

        if ps_conn is None:
            raise ValueError(
                "No connection to the postgres database given. Set the "
                "POSTGRES_URL environment variable."
            )

        store_kwargs = store_kwargs or {}
        try:
            table_name = store_kwargs["table_name"]
            schema_name = store_kwargs["schema_name"]
            content_column = store_kwargs["content_column"]
            embedding_column = store_kwargs["embedding_column"]
            id_column = store_kwargs["id_column"]["name"]
            metadata_columns = [
                column["name"] for column in store_kwargs["metadata_columns"]
            ]
            metadata_json_column = store_kwargs["metadata_json_column"]
        except (KeyError, TypeError) as error:
            raise ValueError(
                "store_kwargs must include the configured table and column names."
            ) from error

        self.embeddings = embeddings
        self.similarity_search_kwargs = similarity_search_kwargs or {}
        self.mmr_search_kwargs = mmr_search_kwargs or {}

        # PGVectorStore opens an existing table. Table creation belongs to the
        # embedding builder so serving a query can never create or reset data.
        vector_engine = PGEngine.from_connection_string(
            make_url(ps_conn).set(drivername="postgresql+psycopg")
        )
        self.store = PGVectorStore.create_sync(
            vector_engine,
            self.embeddings,
            table_name,
            schema_name=schema_name,
            content_column=content_column,
            embedding_column=embedding_column,
            id_column=id_column,
            metadata_columns=metadata_columns,
            metadata_json_column=metadata_json_column,
        )

    def similarity_search(self, query: str) -> list[Document]:
        """Find the documents closest to a query.

        Args:
            query: The text to search for. It is embedded before the search.

        Returns:
            The matching documents, ranked by similarity.
        """
        return self.store.similarity_search(query, **self.similarity_search_kwargs)

    def mmr_search(self, query: str) -> list[Document]:
        """Find documents for a query, trading similarity for variety.

        Args:
            query: The text to search for. It is embedded before the search.

        Returns:
            The matching documents, ranked by maximal marginal relevance.
        """
        return self.store.max_marginal_relevance_search(query, **self.mmr_search_kwargs)

    def similarity_search_by_vec(self, vec: list[float]) -> list[Document]:
        """Find the documents closest to an already embedded query.

        Args:
            vec: The query's embedding, in the embedding model's dimension.

        Returns:
            The matching documents, ranked by similarity.
        """
        return self.store.similarity_search_by_vector(
            vec, **self.similarity_search_kwargs
        )

    def mmr_search_by_vec(self, vec: list[float]) -> list[Document]:
        """Find documents for an already embedded query, favouring variety.

        Args:
            vec: The query's embedding, in the embedding model's dimension.

        Returns:
            The matching documents, ranked by maximal marginal relevance.
        """
        return self.store.max_marginal_relevance_search_by_vector(
            vec, **self.mmr_search_kwargs
        )
