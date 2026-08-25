import os
from pathlib import Path
from typing import Any

from langchain_core.documents import Document
from langchain_postgres import PGVector
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import create_engine
from sqlalchemy import text as sql_text
from sqlalchemy.engine import make_url

from .utils import utils


class PapyriEmbeddings:
    """Create and store embeddings for Scrapyrus documents.

    The class uses a configured embedding model, splits source text into chunks,
    and stores the resulting embeddings in PostgreSQL through PGVector.
    """

    def __init__(
        self,
        embeddings: Any,
        splitter_kwargs: dict[str, Any] | None = None,
        store_kwargs: dict[str, Any] | None = None,
    ):
        """Initialize the text splitter and vector store.

        Args:
            embeddings: The configured model used to embed documents.
            splitter_kwargs: Optional arguments passed to the text splitter.
            store_kwargs: Optional arguments passed to PGVector.

        Raises:
            ValueError: If the ``POSTGRES_URL`` environment variable is not set.
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
    def from_config(cls, path: str | Path) -> "PapyriEmbeddings":
        """Build an embedder from a YAML configuration file.

        Args:
            path: Path to the YAML configuration file.

        Returns:
            A configured embedding service.
        """
        config = utils.load_config(path)
        return cls(embeddings=utils.build(config.pop("embeddings")), **config)

    def compute_document_embeddings(self, text: str, metadata: dict[str, Any]) -> None:
        """Split and embed one source document.

        Args:
            text: Document text to split and embed.
            metadata: Metadata copied to every generated chunk.
        """
        splits = self.splitter.split_documents(
            [
                Document(page_content=text, metadata=metadata),
            ]
        )

        self.store.add_documents(splits)

    def embedd_everything(self) -> int:
        """Embed every non-empty transcription and translation in Scrapyrus.

        Dates and places are grouped by ``tm_id`` and retained as vector-store
        metadata. The source and destination use the database configured by
        ``POSTGRES_URL``.

        Returns:
            The number of source documents embedded.
        """
        query = sql_text(
            """
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
        )

        count = 0
        with self.engine.connect() as connection:
            for row in connection.execute(query).mappings():
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


if __name__ == "__main__":
    import os

    from .settings import load_environment

    load_environment()

    embedder = PapyriEmbeddings.from_config(os.getenv("EMBEDDINGS_CONFIG"))
    embedder.embedd_everything()
