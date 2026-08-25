"""Search a pgvector store for the passages the agent's tools ask for."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from langchain_core.documents import Document
from langchain_postgres import PGVector
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

from .utils import utils


class RetrievalAgent:
    """Answer questions by searching a vector store, without running a model."""

    @classmethod
    def from_config(cls, path: str | Path) -> "RetrievalAgent":
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
            store_kwargs: Keyword arguments for ``PGVector``, such as
                ``collection_name``. ``connection`` is not accepted here.
            similarity_search_kwargs: Keyword arguments applied to every
                similarity search, such as the number of results ``k``.
            mmr_search_kwargs: Keyword arguments applied to every maximal
                marginal relevance search, such as ``k``.

        Raises:
            ValueError: ``POSTGRES_URL`` is unset, or ``store_kwargs`` carries a
                ``connection`` of its own.
        """
        ps_conn = os.getenv("POSTGRES_URL")

        if ps_conn is None:
            raise ValueError(
                "No connection to the postgres database given. Set the "
                "POSTGRES_URL environment variable."
            )

        if store_kwargs is not None and "connection" in store_kwargs:
            raise ValueError(
                "connection is not allowed in store kwargs. use the env variable POSTGRES_URL to set the database connection"
            )

        self.embeddings = embeddings
        self.similarity_search_kwargs = similarity_search_kwargs or {}
        self.mmr_search_kwargs = mmr_search_kwargs or {}

        # SQLAlchemy resolves a bare ``postgresql://`` URL to psycopg2, which is
        # not installed. Naming psycopg3 on the engine keeps that choice local to
        # this store, so POSTGRES_URL stays the one plain URL the sql tools read.
        engine = create_engine(make_url(ps_conn).set(drivername="postgresql+psycopg"))

        self.store = PGVector(
            embeddings=self.embeddings,
            connection=engine,
            **(store_kwargs or {}),
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
