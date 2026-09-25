from langchain.tools import tool
from collections.abc import MutableMapping
from typing import Any

from ..session import retriever
from ..links import tm_id_from_metadata
from .. import sources

def _stamp_links(documents: list[Any]) -> list[Any]:
    """Add each document's public link to its own metadata, in place.

    Args:
        documents: Whatever the retriever returned.

    Returns:
        The same object that was passed in.
    """
    by_tm_id: dict[int, list[MutableMapping[str, Any]]] = {}
    for document in documents or ():
        metadata = getattr(document, "metadata", None)
        if not isinstance(metadata, MutableMapping):
            continue
        tm_id = tm_id_from_metadata(metadata)
        if tm_id is not None:
            by_tm_id.setdefault(tm_id, []).append(metadata)

    if not by_tm_id:
        return documents

    urls = sources.urls_for(by_tm_id.keys())

    for tm_id, metadata_entries in by_tm_id.items():
        url = urls.get(tm_id)
        if url is None:
            continue
        for metadata in metadata_entries:
            metadata["url"] = url

    return documents

@tool(parse_docstring=True)
def similarity_search(query: str):
    """Search the document store for the passages closest to a question.

    The query is embedded with the same model the store was built with, and the
    nearest passages are returned. Use this when you want the best matches for
    one specific question.

    Args:
        query: The text to search for, written as the question or statement the
            passages should answer.

    Returns:
        The matching documents, each with its page content and metadata. How
        many come back is fixed by the retriever's configuration.
    """
    return _stamp_links(retriever().similarity_search(query))


@tool(parse_docstring=True)
def mmr_search(query: str):
    """Search the document store for passages that cover a question broadly.

    Like ``similarity_search``, but the results are picked with maximal marginal
    relevance, which trades some closeness to the query for variety between the
    passages. Use this when the question has several aspects, or when a plain
    similarity search keeps returning near-duplicates.

    Args:
        query: The text to search for, written as the question or statement the
            passages should answer.

    Returns:
        The selected documents, each with its page content and metadata. How
        many come back is fixed by the retriever's configuration.
    """
    return _stamp_links(retriever().mmr_search(query))


@tool(parse_docstring=True)
def similarity_search_by_vec(vec: list[float]):
    """Search the document store with an embedding you already have.

    Same as ``similarity_search``, except the query is given as a vector rather
    than as text, so no embedding step happens here. Only use this when you were
    handed an embedding; otherwise search by text.

    Args:
        vec: The query embedding, whose length must match the store's embedding
            model.

    Returns:
        The matching documents, each with its page content and metadata. How
        many come back is fixed by the retriever's configuration.
    """
    return _stamp_links(retriever().similarity_search_by_vec(vec))


@tool(parse_docstring=True)
def mmr_search_by_vec(vec: list[float]):
    """Search the document store broadly with an embedding you already have.

    Same as ``mmr_search``, except the query is given as a vector rather than as
    text. Only use this when you were handed an embedding; otherwise search by
    text.

    Args:
        vec: The query embedding, whose length must match the store's embedding
            model.

    Returns:
        The selected documents, each with its page content and metadata. How
        many come back is fixed by the retriever's configuration.
    """
    return _stamp_links(retriever().mmr_search_by_vec(vec))
