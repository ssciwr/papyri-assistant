from typing import Any

import pytest

from papyri_backend.tools import pgvec


@pytest.mark.parametrize(
    ("tool", "arguments", "method", "value"),
    [
        (
            pgvec.similarity_search,
            {"query": "Which Oxyrhynchus texts mention a lease?", "corpus": "transcriptions"},
            "similarity_search",
            "Which Oxyrhynchus texts mention a lease?",
        ),
        (
            pgvec.mmr_search,
            {"query": "Find varied evidence about leases", "corpus": "translations"},
            "mmr_search",
            "Find varied evidence about leases",
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
    selected = []
    monkeypatch.setattr(
        pgvec, "retriever", lambda corpus: selected.append(corpus) or fake_retriever
    )

    result = tool.invoke(arguments)

    assert result is fake_retriever.documents
    assert result[0] is fake_retriever.documents[0]
    assert fake_retriever.calls == [(method, value)]
    assert selected == [arguments["corpus"]]


@pytest.mark.parametrize(
    ("tool", "arguments"),
    [
        (pgvec.similarity_search, {"query": "lease", "corpus": "transcriptions"}),
        (pgvec.mmr_search, {"query": "lease", "corpus": "translations"}),
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
    monkeypatch.setattr(pgvec, "retriever", lambda _corpus: fake_retriever)

    with pytest.raises(RuntimeError, match="vector provider unavailable") as raised:
        tool.invoke(arguments)

    assert raised.value is failure
