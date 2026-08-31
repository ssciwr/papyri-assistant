from typing import Any

import pytest

from papyri_backend.tools import pgvec


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
