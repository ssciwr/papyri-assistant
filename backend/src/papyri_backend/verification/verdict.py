"""Read a small model's reply as a pass/fail verdict.

The reviewer is asked for one JSON object and nothing else. This module assumes
it will not always comply, and recovers what it can without the middleware
having to care.

Three outcomes, not two: an unreadable reply is neither a pass nor a fail. It is
``parsed=False``, and the middleware reports that as "unverified" rather than
letting a formatting slip read as an endorsement.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

_THINK_CLOSE = re.compile(r"</\s*think\s*>", re.IGNORECASE)
_JSON_OBJECT = re.compile(r"\{.*?\}", re.DOTALL)
_UNSPECIFIED_PROBLEM = "The reviewer rejected the answer without naming a problem."


@dataclass(frozen=True)
class Verdict:
    """The reviewer's decision about one answer.

    Attributes:
        passed: Whether the answer may be released.
        problems: Sentences the reviewer objected to, empty on a pass.
        parsed: Whether the reply was understood at all. ``False`` means the
            pass is a default rather than a judgement, and the report must say
            so rather than calling it a pass.
    """

    passed: bool
    problems: tuple[str, ...]
    parsed: bool


def parse_verdict(text: str) -> Verdict:
    """Read a verdict out of the reviewer's reply.

    Args:
        text: The reviewer model's raw reply.

    Returns:
        The verdict. An unreadable reply yields ``passed=True, parsed=False``: a
        reviewer that cannot format its answer has told us something about
        itself, not about the answer, and holding a chat answer hostage to that
        would be worse than releasing it with the malfunction recorded.
    """
    payload = _last_json_object(_without_reasoning(text))
    if payload is None:
        return Verdict(passed=True, problems=(), parsed=False)

    raw_verdict = payload.get("verdict")
    if not isinstance(raw_verdict, str):
        return Verdict(passed=True, problems=(), parsed=False)

    passed = raw_verdict.strip().lower() != "fail"
    problems = tuple(
        problem.strip()
        for problem in payload.get("problems") or []
        if isinstance(problem, str) and problem.strip()
    )

    # A rejection with nothing to fix would send the agent round the loop with
    # no guidance, so it is given a generic problem rather than becoming a pass.
    if not passed and not problems:
        problems = (_UNSPECIFIED_PROBLEM,)

    return Verdict(passed=passed, problems=problems, parsed=True)


def _without_reasoning(text: str) -> str:
    """Drop everything up to and including a closing think tag.

    The opening tag is not required: Qwen's chat template consumes it, which is
    why ``default_langchain_agent.yaml`` sets ``inline_reasoning: true``.
    """
    matches = list(_THINK_CLOSE.finditer(text))
    return text[matches[-1].end() :] if matches else text


def _last_json_object(text: str) -> dict | None:
    """Return the last JSON object in a string, or None if there is none.

    The last rather than the first, because a model that reasons about the
    requested format often shows an example of it before answering in it.
    """
    for match in reversed(list(_JSON_OBJECT.finditer(text))):
        try:
            payload = json.loads(match.group())
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return None