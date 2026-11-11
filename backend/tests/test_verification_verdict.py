"""The reviewer's structured output becomes a verdict, and failures stay visible."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from papyri_backend.verification.verdict import ReviewVerdict, read_verdict

UNSPECIFIED = "No problem was named."


def read(result: dict):
    return read_verdict(result, unspecified_problem=UNSPECIFIED)


def parsed(verdict: str, problems: list[str]) -> dict:
    return {"parsed": ReviewVerdict(verdict=verdict, problems=problems)}


def test_a_clean_pass_is_read() -> None:
    verdict = read(parsed("pass", []))

    assert (verdict.passed, verdict.problems, verdict.parsed) == (True, (), True)


def test_a_fail_carries_its_problems() -> None:
    verdict = read(parsed("fail", ["Sentence two is unsupported."]))

    assert verdict.passed is False
    assert verdict.problems == ("Sentence two is unsupported.",)
    assert verdict.parsed is True


def test_a_rejection_without_problems_still_gives_the_agent_something_to_fix() -> None:
    verdict = read(parsed("fail", ["  "]))

    assert verdict.passed is False
    assert verdict.problems == (UNSPECIFIED,)


def test_a_reply_that_did_not_fit_the_schema_is_not_parsed() -> None:
    verdict = read({"parsed": None, "parsing_error": ValueError("bad")})

    assert verdict.parsed is False
    assert verdict.passed is True
    assert verdict.problems == ()


@pytest.mark.parametrize("value", ["failed", "FAIL", "rejected", ""])
def test_the_schema_accepts_only_pass_or_fail(value: str) -> None:
    with pytest.raises(ValidationError):
        ReviewVerdict(verdict=value)


def test_a_problem_quoting_braces_is_kept_whole() -> None:
    verdict = read(parsed("fail", ['the phrase {n} drachmas, see {"a": 1}']))

    assert verdict.problems == ('the phrase {n} drachmas, see {"a": 1}',)
