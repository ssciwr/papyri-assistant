import os
from pathlib import Path
from typing import Any

from langchain_core.documents import Document
from langchain_postgres import PGVector
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import create_engine
from sqlalchemy import text as sql_text
from sqlalchemy.engine import make_url
from tqdm import tqdm
from .utils import utils


class LangChainEmbeddings:
    """Create and store vector embeddings for Scrapyrus documents.

    This service splits source text into chunks, embeds each chunk with the
    configured model, and stores the resulting vectors in PostgreSQL through
    PGVector.

    Attributes:
        embeddings: Model used to produce vector embeddings.
        splitter: Text splitter used to create embeddable chunks.
        engine: SQLAlchemy engine connected to the source database.
        store: PGVector store that receives the embedded chunks.
    """

    def __init__(
        self,
        embeddings: Any,
        splitter_kwargs: dict[str, Any] | None = None,
        store_kwargs: dict[str, Any] | None = None,
    ):
        """Initialize the embedding service.

        Args:
            embeddings: Configured model used to embed documents.
            splitter_kwargs: Arguments passed to
                ``RecursiveCharacterTextSplitter``.
            store_kwargs: Arguments passed to ``PGVector``.

        Raises:
            ValueError: If the ``POSTGRES_URL`` environment variable is unset.
        """
        self.embeddings = embeddings
        self.splitter = RecursiveCharacterTextSplitter(**(splitter_kwargs or {}))

        ps_conn = os.getenv("POSTGRES_URL")
        if ps_conn is None:
            raise ValueError(
                "No connection to the postgres database given. Set the "
                "POSTGRES_URL environment variable."
            )

        self.engine = create_engine(
            make_url(ps_conn).set(drivername="postgresql+psycopg")
        )

        self.store = PGVector(
            embeddings=self.embeddings,
            connection=self.engine,
            **(store_kwargs or {}),
        )

    @classmethod
    def from_config(cls, path: str | Path) -> "LangChainEmbeddings":
        """Create an embedding service from a YAML configuration file.

        Args:
            path: YAML configuration file to load.

        Returns:
            A configured embedding service instance.
        """
        config = utils.load_config(path)
        return cls(embeddings=utils.build(config.pop("embeddings")), **config)

    def compute_document_embeddings(self, text: str, metadata: dict[str, Any]) -> None:
        """Split, embed, and store a source document.

        Args:
            text: Source text to split and embed.
            metadata: Metadata to copy to every generated chunk.
        """
        splits = self.splitter.split_documents(
            [
                Document(page_content=text, metadata=metadata),
            ]
        )

        self.store.add_documents(splits)

    def embedd_selection(self, sql_query: str) -> int:
        """Embed every source document returned by a SQL query.

        The query must return ``transcription_id``, ``source_path``, ``tm_id``,
        ``type``, ``language``, ``text``, ``dates``, and ``places`` columns. The
        query is also wrapped as a subquery to determine the progress-bar total,
        with one trailing semicolon removed before wrapping.

        Args:
            sql_query: Trusted SQL ``SELECT`` statement describing the source
                documents to embed.

        Returns:
            The number of source documents embedded.
        """
        selection = sql_query.removesuffix(";")
        count_query = sql_text(f"SELECT COUNT(*) FROM ({selection}) AS selected_rows")

        count = 0

        with self.engine.connect() as connection:
            length = connection.execute(count_query).scalar_one()

            for row in tqdm(
                connection.execute(sql_text(sql_query)).mappings(),
                desc="rows",
                total=length,
            ):
                metadata = {
                    "source": "scrapyrus",
                    "transcription_id": row["transcription_id"],
                    "source_path": row["source_path"],
                    "tm_id": row["tm_id"],
                    "document_type": row["type"],
                    "language": row["language"],
                    "dates": row["dates"],
                    "places": row["places"],
                }
                self.compute_document_embeddings(row["text"], metadata)
                count += 1

        return count

    def embedd_everything(self) -> int:
        """Embed every non-empty transcription and translation in Scrapyrus.

        Group dates and places by ``tm_id`` and retain them as vector-store
        metadata. Read source documents from and write embeddings to the database
        configured by ``POSTGRES_URL``.

        Returns:
            The number of source documents embedded.
        """
        query = """
            WITH dates AS (
                SELECT
                    tm_id,
                    jsonb_agg(
                        jsonb_build_object(
                            'text', date_text,
                            'not_before_year', not_before_year,
                            'not_after_year', not_after_year,
                            'alternative', alternative
                        ) ORDER BY date_id
                    ) AS values
                FROM orig_dates
                GROUP BY tm_id
            ),
            places AS (
                SELECT
                    tm_id,
                    jsonb_agg(
                        jsonb_build_object(
                            'name', place_name,
                            'full_name', full_place_name,
                            'type', place_type,
                            'granularity', granularity,
                            'tm_place_id', tm_place_id,
                            'pleiades_place_id', pleiades_place_id
                        ) ORDER BY place_id
                    ) AS values
                FROM orig_places
                GROUP BY tm_id
            )
            SELECT
                transcription_id,
                source_path,
                tm_id,
                type,
                language,
                text,
                COALESCE(dates.values, '[]'::jsonb) AS dates,
                COALESCE(places.values, '[]'::jsonb) AS places
            FROM transcriptions
            LEFT JOIN dates USING (tm_id)
            LEFT JOIN places USING (tm_id)
            WHERE text <> ''
            ORDER BY transcription_id
            """
        return self.embedd_selection(query)
