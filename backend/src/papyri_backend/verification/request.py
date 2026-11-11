"""What the reviewer is asked, and how the material reaches it.

The reviewer's checks are in its system prompt in the agent config. This module
builds the message the reviewer judges: the user's question, the answer, and
the evidence retrieved during this turn.

The evidence is fenced. It contains corpus text this project does not control
and SQL the model wrote, and it is being fed to the check that guards the
output: a transcription -- or a crafted database row -- containing
instruction-shaped text must not be able to steer the verdict.

The message template and the fence markers come from the agent config, next to
the reviewer's system prompt, so everything the reviewer reads is in one place.
"""

from __future__ import annotations

from collections.abc import Sequence

REQUEST_PLACEHOLDERS = ("{question}", "{answer}", "{evidence}")
"""Placeholders the configured request template must contain."""


def fence_evidence(body: str, *, start: str, end: str) -> str:
    """Wrap retrieved text so it cannot pose as an instruction.

    Any occurrence of a marker inside the body is defaced first, so that content
    cannot close the fence early and continue as if it were prompt.

    Args:
        body: The rendered evidence.
        start: The line that opens the fence.
        end: The line that closes the fence.

    Returns:
        The same text between the two markers.
    """
    for marker in (start, end):
        body = body.replace(marker, " ".join(marker))
    return f"{start}\n{body}\n{end}"


def build_review_request(
    *,
    template: str,
    evidence_start: str,
    evidence_end: str,
    question: str,
    answer: str,
    evidence: Sequence[str],
) -> str:
    """Assemble the single user message the reviewer sees.

    Args:
        template: The message layout, with ``{question}``, ``{answer}`` and
            ``{evidence}`` placeholders.
        evidence_start: The line that opens the evidence fence.
        evidence_end: The line that closes the evidence fence.
        question: The user's question, without any injected critique.
        answer: The answer text the agent proposes to release.
        evidence: The evidence blocks retrieved during this turn, in call
            order.

    Returns:
        The request body.
    """
    # Said explicitly, so the reviewer can tell "no tools were called" from a
    # missing section.
    body = "\n\n".join(evidence) or (
        "No tools were called during this turn, so there is no evidence."
    )
    return template.format(
        question=question.strip(),
        answer=answer.strip(),
        evidence=fence_evidence(body, start=evidence_start, end=evidence_end),
    )