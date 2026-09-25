"""What the reviewer is asked, and how the material reaches it.

The first four questions are Section 4 of the agentic workflow design, verbatim
in substance. They are narrow on purpose: the reviewer is the same class of
model that wrote the answer, and asking closed questions about text already in
front of it is a much easier task than answering the original question.

Question 5 and the no-tools rule are additions. They carry the weight of the
design's tier 1 check, "the ledger is non-empty", which is deterministic there
and is not built yet.

The evidence is fenced. It contains corpus text this project does not control
and SQL the model wrote, and it is being fed to the check that guards the
output: a transcription -- or a crafted database row -- containing
instruction-shaped text must not be able to steer the verdict.
"""

from __future__ import annotations

from collections.abc import Sequence

from .evidence import EvidenceItem, format_evidence

_FENCE_OPEN = "----- BEGIN EVIDENCE -----"
_FENCE_CLOSE = "----- END EVIDENCE -----"
_REQUEST_TEMPLATE = """QUESTION
{question}

ANSWER
{answer}

EVIDENCE RETRIEVED THIS TURN
{evidence}

Reply with the JSON object only."""


def fence_evidence(body: str) -> str:
    """Wrap retrieved text so it cannot pose as an instruction.

    Any occurrence of a marker inside the body is defaced first, so that content
    cannot close the fence early and continue as if it were prompt.

    Args:
        body: The rendered evidence.

    Returns:
        The same text between the two markers.
    """
    for marker in (_FENCE_OPEN, _FENCE_CLOSE):
        body = body.replace(marker, marker.replace("-----", "- - -"))
    return f"{_FENCE_OPEN}\n{body}\n{_FENCE_CLOSE}"


def build_review_request(
    *, question: str, answer: str, items: Sequence[EvidenceItem]
) -> str:
    """Assemble the single user message the reviewer sees.

    Args:
        question: The user's question, without any injected critique.
        answer: The answer text the agent proposes to release.
        items: The evidence retrieved during this turn, in call order.

    Returns:
        The request body.
    """
    return _REQUEST_TEMPLATE.format(
        question=question.strip(),
        answer=answer.strip(),
        evidence=fence_evidence(format_evidence(items)),
    )