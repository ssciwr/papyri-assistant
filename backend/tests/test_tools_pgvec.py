from typing import Any

import pytest

from papyri_backend.tools import pgvec
from langchain_core.documents import Document

@pytest.mark.parametrize(
    ("tool", "arguments", "method", "value"),
    [
        (
            pgvec.similarity_search,
            {"query": "Which Oxyrhynchus texts mention a lease?"},
            "similarity_search",
            "Which Oxyrhynchus texts mention a lease?",
        ),
        (
            pgvec.mmr_search,
            {"query": "Find varied evidence about leases"},
            "mmr_search",
            "Find varied evidence about leases",
        ),
        (
            pgvec.similarity_search_by_vec,
            {"vec": [0.1, 0.2, 0.3]},
            "similarity_search_by_vec",
            [0.1, 0.2, 0.3],
        ),
        (
            pgvec.mmr_search_by_vec,
            {"vec": [0.4, 0.5, 0.6]},
            "mmr_search_by_vec",
            [0.4, 0.5, 0.6],
        ),
    ],
)
def test_search_tools_forward_input_and_preserve_documents(
    monkeypatch: pytest.MonkeyPatch,
    fake_retriever: Any,
    tool: Any,
    arguments: dict[str, Any],
    method: str,
    value: Any,
) -> None:
    monkeypatch.setattr(pgvec, "retriever", lambda: fake_retriever)

    result = tool.invoke(arguments)

    assert result is fake_retriever.documents
    assert result[0] is fake_retriever.documents[0]
    assert fake_retriever.calls == [(method, value)]


@pytest.mark.parametrize(
    ("tool", "arguments"),
    [
        (pgvec.similarity_search, {"query": "lease"}),
        (pgvec.mmr_search, {"query": "lease"}),
        (pgvec.similarity_search_by_vec, {"vec": [0.1, 0.2]}),
        (pgvec.mmr_search_by_vec, {"vec": [0.1, 0.2]}),
    ],
)
def test_search_tools_do_not_mask_retriever_failures(
    monkeypatch: pytest.MonkeyPatch,
    fake_retriever: Any,
    tool: Any,
    arguments: dict[str, Any],
) -> None:
    failure = RuntimeError("vector provider unavailable")
    fake_retriever.error = failure
    monkeypatch.setattr(pgvec, "retriever", lambda: fake_retriever)

    with pytest.raises(RuntimeError, match="vector provider unavailable") as raised:
        tool.invoke(arguments)

    assert raised.value is failure

class _StubRetriever:
    """A retriever returning fixed documents, for the stamping tests."""

    def __init__(self, documents: list[Any]) -> None:
        self.documents = documents

    def similarity_search(self, query: str) -> list[Any]:
        return self.documents

    def mmr_search(self, query: str) -> list[Any]:
        return self.documents

@pytest.fixture
def link_lookups(monkeypatch: pytest.MonkeyPatch) -> list[list[int]]:
    """Record every batch of ids the stamping asks the database about.

    TM 999 deliberately resolves to nothing, so that the unresolvable case is
    exercised by the same fake.
    """
    lookups: list[list[int]] = []

    def fake_urls_for(tm_ids: Any) -> dict[int, str]:
        wanted = [int(tm_id) for tm_id in tm_ids]
        lookups.append(wanted)
        return {
            tm_id: f"https://papyri.info/editions/p.test/{tm_id}"
            for tm_id in wanted
            if tm_id != 999
        }

    monkeypatch.setattr(pgvec.sources, "urls_for", fake_urls_for)
    return lookups


def test_similarity_search_stamps_the_edition_link(
    monkeypatch: pytest.MonkeyPatch, link_lookups: list[list[int]]
) -> None:
    document = Document(page_content="μίσθωσις οἰκίας", metadata={"tm_id": 123456})
    monkeypatch.setattr(pgvec, "retriever", lambda: _StubRetriever([document]))

    result = pgvec.similarity_search.invoke({"query": "house lease"})

    assert result[0].metadata["url"] == "https://papyri.info/editions/p.test/123456"
    assert link_lookups == [[123456]]


def test_documents_sharing_a_tm_id_cost_one_lookup(
    monkeypatch: pytest.MonkeyPatch, link_lookups: list[list[int]]
) -> None:
    documents = [
        Document(page_content="chunk one", metadata={"tm_id": 555}),
        Document(page_content="chunk two", metadata={"tm_id": 555}),
        Document(page_content="other", metadata={"tm_id": 556}),
    ]
    monkeypatch.setattr(pgvec, "retriever", lambda: _StubRetriever(documents))

    result = pgvec.similarity_search.invoke({"query": "lease"})

    assert link_lookups == [[555, 556]]
    assert result[0].metadata["url"] == result[1].metadata["url"]

def test_a_document_without_a_resolvable_id_is_returned_unchanged(
    monkeypatch: pytest.MonkeyPatch, link_lookups: list[list[int]]
) -> None:
    documents = [
        Document(page_content="keyword hit", metadata={"term": "lease"}),
        Document(page_content="unknown document", metadata={"tm_id": 999}),
    ]
    monkeypatch.setattr(pgvec, "retriever", lambda: _StubRetriever(documents))

    result = pgvec.similarity_search.invoke({"query": "lease"})

    assert "url" not in result[0].metadata
    assert "url" not in result[1].metadata
    assert link_lookups == [[999]]