from typing import Annotated

from langchain.tools import tool
from pydantic import Field

from ..langchain_retrieval import Corpus
from ..session import retriever


CorpusArgument = Annotated[
    Corpus,
    Field(
        description=(
            "Corpus to search. Use transcriptions for original-language wording "
            "and readings; translations for a document's meaning or subject in "
            "translation; and keywords for controlled vocabulary and classification "
            "terms rather than document passages."
        )
    ),
]


@tool(parse_docstring=True)
def similarity_search(query: str, corpus: CorpusArgument):
    """Search one published corpus for the items closest to a question.

    Transcriptions contain original-language chunks, translations contain
    translated chunks, and keywords contain exact vocabulary candidates.

    Args:
        query: The text to search for, written as the question or statement the
            passages should answer.

    Returns:
        The matching documents, each with its page content and metadata. How
        many come back is fixed by the retriever's configuration.
    """
    return retriever(corpus).similarity_search(query)


@tool(parse_docstring=True)
def mmr_search(query: str, corpus: CorpusArgument):
    """Search one corpus for varied passages or vocabulary candidates.

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
    return retriever(corpus).mmr_search(query)
