from langchain.tools import tool


def _retriever():
    from .. import (
        chat,
    )  # deferred: chat -> langchain_agent -> tools is circular at import time

    if chat.RETRIEVER is None:
        raise ValueError("global RETRIEVER object doesn't exist")
    return chat.RETRIEVER


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
    return _retriever().similarity_search(query)


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
    return _retriever().mmr_search(query)


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
    return _retriever().similarity_search_by_vec(vec)


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
    return _retriever().mmr_search_by_vec(vec)
