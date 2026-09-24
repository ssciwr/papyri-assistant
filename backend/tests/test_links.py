# backend/tests/test_links.py
import pytest

from papyri_backend import links


@pytest.mark.parametrize(
    ("hybrid_id", "expected"),
    [
        ("p.koeln.sarapion;;15", "https://papyri.info/editions/p.koeln.sarapion/15"),
        ("p.genova;5;198", "https://papyri.info/editions/p.genova/5/198"),
        ("p.iand;5;74", "https://papyri.info/editions/p.iand/5/74"),
    ],
)
def test_papyri_info_url_rearranges_a_hybrid_id(hybrid_id, expected) -> None:
    assert links.papyri_info_url(hybrid_id) == expected


@pytest.mark.parametrize("hybrid_id", [None, "", ";;", "   "])
def test_papyri_info_url_rejects_unusable_ids(hybrid_id) -> None:
    assert links.papyri_info_url(hybrid_id) is None


@pytest.mark.parametrize("tm_id", [123456, "123456"])
def test_trismegistos_url_accepts_int_or_str(tm_id) -> None:
    assert links.trismegistos_url(tm_id) == "https://www.trismegistos.org/text/123456"


@pytest.mark.parametrize("tm_id", [None, "", "not-a-number", 0, -1])
def test_trismegistos_url_rejects_unusable_ids(tm_id) -> None:
    assert links.trismegistos_url(tm_id) is None


def test_tm_id_found_at_top_level() -> None:
    assert links.tm_id_from_metadata({"tm_id": 123456}) == 123456


def test_tm_id_found_nested_in_metadata_json() -> None:
    assert links.tm_id_from_metadata({"metadata": {"tm_id": "123456"}}) == 123456



def test_tm_id_absent_returns_none() -> None:
    assert links.tm_id_from_metadata({"source": "scrapyrus"}) is None


def test_tm_id_returns_none_for_non_dict() -> None:
    assert links.tm_id_from_metadata({"metadata": "not a dict"}) is None