"""Discover and search the embedding corpora published by Scrapyrus."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
import os
import re
from typing import Any, Literal, cast

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_postgres.v2.engine import PGEngine
from langchain_postgres.v2.indexes import DistanceStrategy
from langchain_postgres.v2.vectorstores import PGVectorStore
import psycopg
from sqlalchemy.engine import make_url


Corpus = Literal["transcriptions", "translations", "keywords"]
EXPECTED_CONTRACT_VERSION = 1
EMBEDDING_METADATA_TABLE = "embedding_table_metadata"


@dataclass(frozen=True)
class CorpusMapping:
    """The fixed, versioned mapping from one logical corpus to PostgreSQL."""

    table_name: str
    id_column: str
    content_column: str
    metadata_columns: tuple[str, ...]


CORPUS_MAPPINGS: dict[Corpus, CorpusMapping] = {
    "transcriptions": CorpusMapping(
        "transcription_embeddings",
        "chunk_id",
        "document_text",
        ("xml_id", "chunk_index", "source_path", "tm_id", "language"),
    ),
    "translations": CorpusMapping(
        "translation_embeddings",
        "chunk_id",
        "document_text",
        ("xml_id", "chunk_index", "source_path", "tm_id", "language"),
    ),
    "keywords": CorpusMapping(
        "keyword_embeddings", "keyword", "keyword", ("keyword",)
    ),
}
SUPPORTED_EMBEDDING_PROVIDERS = frozenset(
    {"openai", "vllm", "voyageai", "mistralai", "huggingface"}
)


class EmbeddingContractError(RuntimeError):
    """Raised when a published corpus cannot safely be queried."""


@dataclass(frozen=True)
class EmbeddingSpecification:
    """Compatibility-affecting settings published for an embedding table."""

    table_name: str
    model_name: str
    embedding_size: int
    provider: str
    provider_options: Mapping[str, Any]
    endpoint_profile: str | None
    contract_version: int

    @property
    def identity(self) -> str:
        """Return a stable, non-secret identifier for vector provenance."""

        value = {
            "contract_version": self.contract_version,
            "endpoint_profile": self.endpoint_profile,
            "model_name": self.model_name,
            "provider": self.provider,
            "provider_options": self.provider_options,
        }
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"))
        return f"sha256:{hashlib.sha256(encoded.encode()).hexdigest()}"


def _env_key(prefix: str, value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").upper()
    return f"{prefix}_{normalized}"


def _endpoint(specification: EmbeddingSpecification) -> str | None:
    if specification.endpoint_profile is None:
        return None
    variable = _env_key("EMBEDDING_ENDPOINT", specification.endpoint_profile)
    endpoint = os.getenv(variable)
    if not endpoint:
        raise EmbeddingContractError(
            f"{specification.table_name!r} requires endpoint profile "
            f"{specification.endpoint_profile!r}; set {variable}."
        )
    return endpoint


def _secret(provider: str) -> str | None:
    variables = {
        "openai": "OPENAI_API_KEY",
        "vllm": "VLLM_API_KEY",
        "voyageai": "VOYAGE_API_KEY",
        "mistralai": "MISTRAL_API_KEY",
    }
    variable = variables.get(provider)
    if variable is None:
        return None
    value = os.getenv(variable)
    if provider == "vllm":
        return value or "EMPTY"
    if not value:
        raise EmbeddingContractError(
            f"Embedding provider {provider!r} requires {variable}."
        )
    return value


def _only_options(
    specification: EmbeddingSpecification,
    allowed: set[str],
    required: set[str] | None = None,
) -> dict[str, Any]:
    unknown = set(specification.provider_options) - allowed
    if unknown:
        raise EmbeddingContractError(
            f"{specification.table_name!r} has unsupported {specification.provider!r} "
            f"embedding options: {sorted(unknown)}"
        )
    missing = (required or set()) - set(specification.provider_options)
    if missing:
        raise EmbeddingContractError(
            f"{specification.table_name!r} does not record effective "
            f"{specification.provider!r} embedding options: {sorted(missing)}"
        )
    return dict(specification.provider_options)


def build_embeddings(specification: EmbeddingSpecification) -> Embeddings:
    """Construct an allowlisted LangChain embedding integration."""

    provider = specification.provider
    endpoint = _endpoint(specification)
    if provider in {"openai", "vllm"}:
        from langchain_openai import OpenAIEmbeddings

        options = _only_options(
            specification,
            {"dimensions", "check_embedding_ctx_length"},
            {"check_embedding_ctx_length"},
        )
        return OpenAIEmbeddings(
            model=specification.model_name,
            api_key=cast(Any, _secret(provider)),
            base_url=endpoint,
            **options,
        )
    if provider == "voyageai":
        from langchain_voyageai import VoyageAIEmbeddings

        options = _only_options(
            specification,
            {
                "output_dimension",
                "truncation",
                "batch_size",
                "document_input_type",
                "query_input_type",
            },
            {"truncation", "batch_size", "document_input_type", "query_input_type"},
        )
        if options.pop("document_input_type", None) != "document":
            raise EmbeddingContractError("VoyageAI document_input_type must be 'document'.")
        if options.pop("query_input_type", None) != "query":
            raise EmbeddingContractError("VoyageAI query_input_type must be 'query'.")
        return VoyageAIEmbeddings(
            model=specification.model_name,
            api_key=cast(Any, _secret(provider)),
            base_url=endpoint,
            **options,
        )
    if provider == "mistralai":
        from langchain_mistralai import MistralAIEmbeddings

        options = _only_options(specification, set())
        kwargs: dict[str, Any] = {
            "model": specification.model_name,
            "api_key": _secret(provider),
            **options,
        }
        if endpoint is not None:
            kwargs["endpoint"] = endpoint
        return MistralAIEmbeddings(**kwargs)
    if provider == "huggingface":
        from langchain_huggingface import HuggingFaceEmbeddings

        options = _only_options(
            specification,
            {
                "model_revision",
                "normalize_embeddings",
                "truncate_dim",
                "document_prompt_name",
                "query_prompt_name",
            },
            {"normalize_embeddings"},
        )
        revision = options.pop("model_revision", None)
        normalize = options.pop("normalize_embeddings", False)
        truncate_dim = options.pop("truncate_dim", None)
        document_prompt = options.pop("document_prompt_name", None)
        query_prompt = options.pop("query_prompt_name", None)
        encode_kwargs = {"normalize_embeddings": normalize}
        query_encode_kwargs = {"normalize_embeddings": normalize}
        if truncate_dim is not None:
            encode_kwargs["truncate_dim"] = truncate_dim
            query_encode_kwargs["truncate_dim"] = truncate_dim
        if document_prompt is not None:
            encode_kwargs["prompt_name"] = document_prompt
        if query_prompt is not None:
            query_encode_kwargs["prompt_name"] = query_prompt
        return HuggingFaceEmbeddings(
            model_name=specification.model_name,
            model_kwargs={} if revision is None else {"revision": revision},
            encode_kwargs=encode_kwargs,
            query_encode_kwargs=query_encode_kwargs,
        )
    raise EmbeddingContractError(
        f"{specification.table_name!r} names unsupported embedding provider "
        f"{provider!r}."
    )


def _row_value(row: Any, key: str, index: int) -> Any:
    return row[key] if isinstance(row, Mapping) else row[index]


def discover_specifications(
    connection: psycopg.Connection[Any],
) -> dict[Corpus, EmbeddingSpecification]:
    """Read and validate the three required published specifications."""

    table_names = tuple(mapping.table_name for mapping in CORPUS_MAPPINGS.values())
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT table_name, model_name, embedding_size, provider, "
                f"provider_options, endpoint_profile, contract_version "
                f"FROM {EMBEDDING_METADATA_TABLE} "
                "WHERE table_name = ANY(%s)",
                (list(table_names),),
            )
            rows = cursor.fetchall()
    except Exception as error:
        connection.rollback()
        raise EmbeddingContractError(
            "Could not read the Scrapyrus embedding contract. Publish embeddings "
            "with a current Scrapyrus release before starting the assistant."
        ) from error

    by_table = {str(_row_value(row, "table_name", 0)): row for row in rows}
    discovered: dict[Corpus, EmbeddingSpecification] = {}
    for corpus, mapping in CORPUS_MAPPINGS.items():
        row = by_table.get(mapping.table_name)
        if row is None:
            raise EmbeddingContractError(
                f"Missing embedding metadata for {mapping.table_name!r}; ingest and "
                "publish the corpus with Scrapyrus."
            )
        size = _row_value(row, "embedding_size", 2)
        provider = _row_value(row, "provider", 3)
        options = _row_value(row, "provider_options", 4)
        version = _row_value(row, "contract_version", 6)
        if size is None or int(size) < 1:
            raise EmbeddingContractError(
                f"{mapping.table_name!r} has no published embedding dimension."
            )
        if provider is None or not str(provider):
            raise EmbeddingContractError(
                f"{mapping.table_name!r} has no embedding provider provenance."
            )
        if str(provider) not in SUPPORTED_EMBEDDING_PROVIDERS:
            raise EmbeddingContractError(
                f"{mapping.table_name!r} names unsupported embedding provider "
                f"{provider!r}."
            )
        if int(version) != EXPECTED_CONTRACT_VERSION:
            raise EmbeddingContractError(
                f"{mapping.table_name!r} uses embedding contract version {version}; "
                f"this assistant requires {EXPECTED_CONTRACT_VERSION}."
            )
        if not isinstance(options, Mapping):
            raise EmbeddingContractError(
                f"{mapping.table_name!r} has invalid provider_options metadata."
            )
        discovered[corpus] = EmbeddingSpecification(
            table_name=mapping.table_name,
            model_name=str(_row_value(row, "model_name", 1)),
            embedding_size=int(size),
            provider=str(provider),
            provider_options=dict(options),
            endpoint_profile=(
                None
                if _row_value(row, "endpoint_profile", 5) is None
                else str(_row_value(row, "endpoint_profile", 5))
            ),
            contract_version=int(version),
        )
    return discovered


def _validate_table(
    connection: psycopg.Connection[Any],
    mapping: CorpusMapping,
    specification: EmbeddingSpecification,
) -> str:
    embedding_column = (
        "search_embedding"
        if 2_000 < specification.embedding_size <= 4_000
        else "embedding"
    )
    required = {
        mapping.id_column,
        mapping.content_column,
        embedding_column,
        *mapping.metadata_columns,
    }
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT a.attname, format_type(a.atttypid, a.atttypmod) "
            "FROM pg_attribute AS a "
            "WHERE a.attrelid = to_regclass(%s) AND a.attnum > 0 "
            "AND NOT a.attisdropped",
            (f"public.{mapping.table_name}",),
        )
        columns = {
            str(_row_value(row, "attname", 0)): str(_row_value(row, "format_type", 1))
            for row in cursor.fetchall()
        }
    missing = sorted(required - columns.keys())
    if missing:
        raise EmbeddingContractError(
            f"{mapping.table_name!r} is missing required columns: {missing}."
        )
    expected_type = (
        f"halfvec({specification.embedding_size})"
        if embedding_column == "search_embedding"
        else f"vector({specification.embedding_size})"
    )
    if columns[embedding_column] != expected_type:
        raise EmbeddingContractError(
            f"{mapping.table_name!r}.{embedding_column} is "
            f"{columns[embedding_column]!r}; expected {expected_type!r}."
        )
    return embedding_column


class LangChainRetriever:
    """A validated retrieval facade for one published corpus."""

    def __init__(
        self,
        *,
        corpus: Corpus,
        specification: EmbeddingSpecification,
        embeddings: Embeddings,
        store: PGVectorStore,
        similarity_search_kwargs: Mapping[str, Any] | None = None,
        mmr_search_kwargs: Mapping[str, Any] | None = None,
    ) -> None:
        self.corpus = corpus
        self.specification = specification
        self.embeddings = embeddings
        self.store = store
        self.similarity_search_kwargs = dict(similarity_search_kwargs or {"k": 4})
        self.mmr_search_kwargs = dict(
            mmr_search_kwargs or {"k": 4, "fetch_k": 20, "lambda_mult": 0.5}
        )

    @property
    def specification_id(self) -> str:
        return self.specification.identity

    def similarity_search(self, query: str) -> list[Document]:
        return self.store.similarity_search(query, **self.similarity_search_kwargs)

    def mmr_search(self, query: str) -> list[Document]:
        return self.store.max_marginal_relevance_search(query, **self.mmr_search_kwargs)

    def _validate_vector(self, vec: list[float], specification_id: str) -> None:
        if specification_id != self.specification_id:
            raise ValueError(
                f"Vector provenance {specification_id!r} is incompatible with "
                f"corpus {self.corpus!r} ({self.specification_id})."
            )
        if len(vec) != self.specification.embedding_size:
            raise ValueError(
                f"Vector has {len(vec)} dimensions, but corpus {self.corpus!r} "
                f"requires {self.specification.embedding_size}."
            )

    def similarity_search_by_vec(
        self, vec: list[float], specification_id: str
    ) -> list[Document]:
        self._validate_vector(vec, specification_id)
        return self.store.similarity_search_by_vector(
            vec, **self.similarity_search_kwargs
        )

    def mmr_search_by_vec(
        self, vec: list[float], specification_id: str
    ) -> list[Document]:
        self._validate_vector(vec, specification_id)
        return self.store.max_marginal_relevance_search_by_vector(
            vec, **self.mmr_search_kwargs
        )


def build_retrievers(
    connection: psycopg.Connection[Any],
    *,
    similarity_search_kwargs: Mapping[str, Any] | None = None,
    mmr_search_kwargs: Mapping[str, Any] | None = None,
) -> tuple[dict[Corpus, LangChainRetriever], PGEngine]:
    """Build all corpus retrievers atomically around one owned PGEngine."""

    database_url = os.getenv("POSTGRES_URL")
    if database_url is None:
        raise EmbeddingContractError("Set POSTGRES_URL before loading retrievers.")
    specifications = discover_specifications(connection)
    engine = PGEngine.from_connection_string(
        make_url(database_url).set(drivername="postgresql+psycopg")
    )
    clients: dict[str, Embeddings] = {}
    retrievers: dict[Corpus, LangChainRetriever] = {}
    try:
        for corpus, mapping in CORPUS_MAPPINGS.items():
            specification = specifications[corpus]
            embedding_column = _validate_table(connection, mapping, specification)
            client = clients.get(specification.identity)
            if client is None:
                client = build_embeddings(specification)
                probe = client.embed_query("Scrapyrus embedding readiness probe")
                if len(probe) != specification.embedding_size:
                    raise EmbeddingContractError(
                        f"{mapping.table_name!r} publishes "
                        f"{specification.embedding_size} dimensions, but its query "
                        f"provider returned {len(probe)}."
                    )
                clients[specification.identity] = client
            store = PGVectorStore.create_sync(
                engine,
                client,
                mapping.table_name,
                schema_name="public",
                content_column=mapping.content_column,
                embedding_column=embedding_column,
                id_column=mapping.id_column,
                metadata_columns=list(mapping.metadata_columns),
                metadata_json_column=None,
                distance_strategy=DistanceStrategy.COSINE_DISTANCE,
            )
            retrievers[corpus] = LangChainRetriever(
                corpus=corpus,
                specification=specification,
                embeddings=client,
                store=store,
                similarity_search_kwargs=similarity_search_kwargs,
                mmr_search_kwargs=mmr_search_kwargs,
            )
    except Exception:
        close_vector_engine(engine)
        raise
    return retrievers, engine


def close_vector_engine(engine: PGEngine) -> None:
    """Synchronously dispose a PGEngine created for synchronous stores."""

    # langchain-postgres currently exposes only an async public close method,
    # although ``from_connection_string`` owns a background loop specifically
    # for its synchronous facade.
    if hasattr(engine, "_run_as_sync") and hasattr(engine, "_pool"):
        engine._run_as_sync(engine._pool.dispose())
    else:  # Small test doubles and future engines with a synchronous close.
        engine.close()
