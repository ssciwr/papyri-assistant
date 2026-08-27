import os
from pathlib import Path
from typing import Any

from langchain_core.documents import Document
from langchain_postgres.v2.engine import Column, PGEngine
from langchain_postgres.v2.vectorstores import PGVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import create_engine, inspect
from sqlalchemy import text as sql_text
from sqlalchemy.engine import make_url
from tqdm import tqdm

from .utils import utils


class LangChainEmbeddings:
    """Create and store vector embeddings for Scrapyrus documents.

    This service splits source text into chunks, embeds each chunk with the
    configured model, and stores the resulting vectors in PostgreSQL through
    PGVectorStore.

    Attributes:
        embeddings: Model used to produce vector embeddings.
        splitter: Text splitter used to create embeddable chunks.
        engine: SQLAlchemy engine connected to the source database.
        store: PGVectorStore table that receives the embedded chunks.
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
            store_kwargs: Table contract used to create and open a
                ``PGVectorStore`` table.

        Raises:
            ValueError: If ``POSTGRES_URL`` is unset or ``store_kwargs`` does
                not describe a valid PGVectorStore table.
        """
        self.embeddings = embeddings
        self.splitter = RecursiveCharacterTextSplitter(**(splitter_kwargs or {}))
        self._validate_store_kwargs(store_kwargs)
        self.store_kwargs = store_kwargs

        ps_conn = os.getenv("POSTGRES_URL")
        if ps_conn is None:
            raise ValueError(
                "No connection to the postgres database given. Set the "
                "POSTGRES_URL environment variable."
            )

        database_url = make_url(ps_conn).set(drivername="postgresql+psycopg")
        self.engine = create_engine(database_url)
        self.vector_engine = PGEngine.from_connection_string(database_url)
        self.store = self._open_store()

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

    @staticmethod
    def _validate_store_kwargs(store_kwargs: dict[str, Any] | None) -> None:
        """Raise ValueError when required table settings are missing.

        Args:
            store_kwargs: PGVectorStore table settings from the embedding
                configuration.

        Raises:
            ValueError: If a required setting is missing.
        """
        if not isinstance(store_kwargs, dict):
            raise ValueError("store_kwargs must be a mapping.")

        required_keys = (
            "table_name",
            "schema_name",
            "vector_size",
            "content_column",
            "embedding_column",
            "id_column",
            "metadata_columns",
            "metadata_json_column",
        )
        missing = [key for key in required_keys if key not in store_kwargs]
        if missing:
            raise ValueError(f"store_kwargs is missing: {', '.join(missing)}.")

        columns = [store_kwargs["id_column"], *store_kwargs["metadata_columns"]]
        for column in columns:
            missing = [
                key for key in ("name", "data_type", "nullable") if key not in column
            ]
            if missing:
                raise ValueError(
                    f"store_kwargs column is missing: {', '.join(missing)}."
                )

    def _open_store(self, *, reset: bool = False) -> PGVectorStore:
        """Open the configured PGVectorStore table.

        Args:
            reset: Whether to replace the existing table with an empty one.

        Returns:
            A synchronous PGVectorStore connected to the configured table.
        """
        table_name = self.store_kwargs["table_name"]
        schema_name = self.store_kwargs["schema_name"]
        id_column = self.store_kwargs["id_column"]
        metadata_columns = self.store_kwargs["metadata_columns"]
        table_exists = inspect(self.engine).has_table(table_name, schema=schema_name)

        # PGVectorStore.create_sync opens an existing table; table creation is
        # deliberately kept here so normal embedding and destructive reset use
        # the same schema settings.
        if reset or not table_exists:
            self.vector_engine.init_vectorstore_table(
                table_name,
                self.store_kwargs["vector_size"],
                schema_name=schema_name,
                content_column=self.store_kwargs["content_column"],
                embedding_column=self.store_kwargs["embedding_column"],
                id_column=Column(**id_column),
                metadata_columns=[Column(**column) for column in metadata_columns],
                metadata_json_column=self.store_kwargs["metadata_json_column"],
                overwrite_existing=reset,
            )

        return PGVectorStore.create_sync(
            self.vector_engine,
            self.embeddings,
            table_name,
            schema_name=schema_name,
            content_column=self.store_kwargs["content_column"],
            embedding_column=self.store_kwargs["embedding_column"],
            id_column=id_column["name"],
            metadata_columns=[column["name"] for column in metadata_columns],
            metadata_json_column=self.store_kwargs["metadata_json_column"],
        )

    def compute_document_embeddings(
        self, text: str, metadata: dict[str, Any], source: str = "scrapyrus"
    ) -> None:
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
        transcription_id = metadata["transcription_id"]
        ids = [f"{source}:{transcription_id}:{index}" for index in range(len(splits))]
        self.store.add_documents(splits, ids=ids)

    def embedd_selection(self, sql_query: str, source: str = "scrapyrus") -> int:
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
                    "source": source,
                    "transcription_id": str(row["transcription_id"]),
                    "source_path": row["source_path"],
                    "tm_id": row["tm_id"],
                    "document_type": row["type"],
                    "language": row["language"],
                    "dates": row["dates"],
                    "places": row["places"],
                }
                self.compute_document_embeddings(row["text"], metadata, source=source)
                count += 1

        return count

    def embedd_everything(self, source: str = "scrapyrus") -> int:
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
        return self.embedd_selection(query, source=source)

    def reset_everything(self) -> None:
        """Replace the configured vector-store table with an empty equivalent.

        This operation destroys every embedding in the configured table. It does
        not affect the source tables or other PostgreSQL tables.
        """
        self.store = self._open_store(reset=True)

    def rebuild_everything(self, source: str = "scrapyrus") -> int:
        """Replace the vector-store table and embed the complete source corpus.

        Args:
            source: Namespace included in chunk IDs and stored metadata.

        Returns:
            The number of source documents embedded.
        """
        self.reset_everything()
        return self.embedd_everything(source=source)
