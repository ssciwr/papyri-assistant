"""The reviewer's reply is read tolerantly, and its failures stay visible."""

from __future__ import annotations

import json

import pytest

from papyri_backend.verification.verdict import parse_verdict


def test_a_clean_pass_is_read() -> None:
    verdict = parse_verdict('{"verdict": "pass", "problems": []}')

    assert (verdict.passed, verdict.problems, verdict.parsed) == (True, (), True)


def test_a_fail_carries_its_problems() -> None:
    verdict = parse_verdict(
        '{"verdict": "fail", "problems": ["Sentence two is unsupported."]}'
    )

    assert verdict.passed is False
    assert verdict.problems == ("Sentence two is unsupported.",)
    assert verdict.parsed is True


@pytest.mark.parametrize(
    "reply",
    [
        'Here is my review:\n{"verdict": "pass", "problems": []}',
        '```json\n{"verdict": "pass", "problems": []}\n```',
        '{"verdict": "pass", "problems": []}\nI hope that helps.',
        '<think>weighing it up</think>{"verdict": "pass", "problems": []}',
    ],
)
def test_a_verdict_survives_the_wrapping_small_models_add(reply: str) -> None:
    assert parse_verdict(reply).parsed is True


def test_the_last_object_wins_over_a_quoted_example() -> None:
    reply = (
        'The format is {"verdict": "pass", "problems": []}. My answer:\n'
        '{"verdict": "fail", "problems": ["Overstated."]}'
    )

    verdict = parse_verdict(reply)

    assert verdict.passed is False
    assert verdict.problems == ("Overstated.",)


def test_a_rejection_without_problems_still_gives_the_agent_something_to_fix() -> None:
    verdict = parse_verdict('{"verdict": "fail", "problems": []}')

    assert verdict.passed is False
    assert len(verdict.problems) == 1


@pytest.mark.parametrize(
    "reply",
    [
        pytest.param("Looks fine to me.", id="no-json-object"),
        pytest.param('{"problems": ["something"]}', id="no-usable-verdict"),
    ],
)
def test_an_unreadable_reply_is_not_parsed(reply: str) -> None:
    verdict = parse_verdict(reply)

    assert verdict.parsed is False
    assert verdict.passed is True
    assert verdict.problems == ()

def test_a_verdict_is_read_whatever_its_case() -> None:
    verdict = parse_verdict('{"verdict": "FAIL", "problems": ["Overstated."]}')

    assert verdict.passed is False
    assert verdict.parsed is True


def test_a_problem_quoting_a_brace_is_still_a_rejection() -> None:
    """The reviewer quotes the sentence it objects to, braces and all.

    Reading the reply with a pattern stopped at the first "}", so this reply
    parsed as nothing and the rejection was released as "unverified". The
    failure direction is what made it serious: a fail became a release.
    """
    reply = '{"verdict": "fail", "problems": ["the phrase {n} drachmas is wrong"]}'

    verdict = parse_verdict(reply)

    assert verdict.parsed is True
    assert verdict.passed is False
    assert verdict.problems == ("the phrase {n} drachmas is wrong",)


def test_a_nested_object_does_not_shadow_the_verdict() -> None:
    # Decoding skips past each object it reads, so an object quoted inside a
    # problem is not mistaken for the "last" object in the reply.
    reply = json.dumps({"verdict": "fail", "problems": ['see {"a": 1} above']})

    verdict = parse_verdict(reply)

    assert verdict.parsed is True
    assert verdict.passed is False
    assert verdict.problems == ('see {"a": 1} above',)

