"""The reviewer's verdict, returned as structured output rather than parsed text.

The reviewer model is called with ``ReviewVerdict`` as its output schema, so
the model server returns the verdict as data and nothing has to be read out of
free text.

Three outcomes, not two: a reply that does not fit the schema is neither a pass
nor a fail. It is ``parsed=False``, and the middleware reports that as
"unverified" rather than letting a formatting slip read as an endorsement.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field


class ReviewVerdict(BaseModel):
    """The reviewer's verdict on one answer."""

    verdict: Literal["pass", "fail"]
    problems: list[str] = Field(default_factory=list)


@dataclass(frozen=True)
class Verdict:
    """The reviewer's decision about one answer.

    Attributes:
        passed: Whether the answer may be released.
        problems: Claims the reviewer objected to, each quoted with the
            sentence that contains it; empty on a pass.
        parsed: Whether the reply was understood at all. ``False`` means the
            pass is a default rather than a judgement, and the report must say
            so rather than calling it a pass.
    """

    passed: bool
    problems: tuple[str, ...]
    parsed: bool


def read_verdict(result: dict[str, Any], *, unspecified_problem: str) -> Verdict:
    """Turn the reviewer's structured output into a verdict.

    Args:
        result: What ``with_structured_output(ReviewVerdict, include_raw=True)``
            returns: ``"parsed"`` holds a ``ReviewVerdict``, or ``None`` when
            the reply did not fit the schema.
        unspecified_problem: The problem given to a rejection that names
            none, from the agent config.

    Returns:
        The verdict. A reply that did not fit yields ``passed=True,
        parsed=False``: a reviewer that cannot format its answer has told us
        something about itself, not about the answer, and holding a chat answer
        hostage to that would be worse than releasing it with the malfunction
        recorded.
    """
    reply = result.get("parsed")
    if not isinstance(reply, ReviewVerdict):
        return Verdict(passed=True, problems=(), parsed=False)

    problems = tuple(problem.strip() for problem in reply.problems if problem.strip())
    # A rejection with nothing to fix would send the agent round the loop with
    # no guidance, so it is given a generic problem rather than becoming a pass.
    if reply.verdict == "fail" and not problems:
        problems = (unspecified_problem,)

    return Verdict(passed=reply.verdict == "pass", problems=problems, parsed=True)
