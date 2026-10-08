"""Measure the verification gate against a fixed question set.

This measures the GATE, not answer correctness: how often the reviewer returns
a readable verdict, how often it sends an answer back to be rewritten, how much
evidence a turn rested on, how many links the answer carried, and what a turn
costs in wall-clock time. Whether the answers are *right* is not measured here,
and no number this module produces should be read as saying so.

The run record names the agent config and the question set it ran against, so a
later run can be compared with it. Records are written locally and are not part
of the repository.
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

# Trailing ")" and "]" are excluded so a markdown link yields the url alone.
_LINK = re.compile(
    r"https?://(?:www\.)?(?:papyri\.info|trismegistos\.org)/[^\s<>\"')\]]+"
)
_NO_REPORT = "no-report"


def load_questions(path: str | Path) -> list[dict[str, Any]]:
    """Read the question set.

    Args:
        path: The questions file.

    Returns:
        One mapping per question, in file order.

    Raises:
        ValueError: The file carries no questions. Raised rather than returning
            an empty list, because a run over zero questions otherwise looks
            like a run that found nothing to criticise.
    """
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    questions = payload.get("questions")
    if not isinstance(questions, list) or not questions:
        raise ValueError(f"{path} carries no questions")
    return questions


def run_question(agent: Any, text: str) -> dict[str, Any]:
    """Ask one question and record what the gate did with the answer.

    Args:
        agent: An agent whose conversation is empty, so that one question's
            history is not the next question's context.
        text: The question to ask.

    Returns:
        The answer, the gate's verdict and the turn's cost. ``verdict`` is
        ``"no-report"`` when no reviewer is configured, which is distinct from
        the reviewer's own ``"skipped"``.
    """
    message = {"role": "user", "content": [{"type": "text", "text": text}]}
    answer = ""
    report: dict[str, Any] = {}

    started = time.monotonic()
    for event in agent.stream_single_turn(message):
        if event["type"] == "text":
            answer += event["content"]
        elif event["type"] == "verification":
            report = event["verification"] or {}
    elapsed = time.monotonic() - started

    return {
        "answer": answer.strip(),
        "links": len(set(_LINK.findall(answer))),
        "verdict": report.get("verdict", _NO_REPORT),
        "parsed": report.get("parsed"),
        "retries": report.get("retries", 0),
        "evidence_count": report.get("evidence_count", 0),
        "problems": report.get("problems", []),
        "seconds": round(elapsed, 2),
    }


def summarise(results: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Reduce a run to the handful of numbers a pull request quotes.

    Args:
        results: One entry per question, as ``run_question`` returns them.

    Returns:
        The summary. ``parse_rate`` counts only turns the reviewer actually
        judged: a turn it never saw says nothing about its formatting, and
        folding those in would flatter or damn it for the wrong reason.
    """
    reviewed = [result for result in results if result.get("parsed") is not None]
    seconds = [result["seconds"] for result in results] or [0.0]
    return {
        "questions": len(results),
        "reviewed": len(reviewed),
        "parse_rate": (
            round(sum(1 for result in reviewed if result["parsed"]) / len(reviewed), 3)
            if reviewed
            else None
        ),
        "rewritten": sum(1 for result in results if result.get("retries")),
        "unverified": sum(
            1 for result in results if result.get("verdict") == "unverified"
        ),
        "fastest_seconds": min(seconds),
        "slowest_seconds": max(seconds),
    }


def build_record(
    *,
    results: Sequence[dict[str, Any]],
    config: str,
    questions_file: str,
    run_at: datetime | None = None,
) -> dict[str, Any]:
    """Assemble the run record, inputs first.

    Args:
        results: One entry per question.
        config: The agent config the run used.
        questions_file: The question set the run used.
        run_at: The run's timestamp. Supplied by tests; defaults to now in UTC.

    Returns:
        The record, ready to serialise.
    """
    moment = run_at or datetime.now(UTC)
    return {
        "run_at": moment.isoformat(timespec="seconds"),
        "config": config,
        "questions_file": questions_file,
        "summary": summarise(results),
        "results": list(results),
    }


def write_record(record: dict[str, Any], directory: str | Path) -> Path:
    """Write a run record, named after the moment it was produced.

    Args:
        record: The record to write.
        directory: Where run records are kept. Created if it does not exist.

    Returns:
        The file written.
    """
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=True)
    # Colons are legal on this filesystem but awkward in shells and on Windows.
    destination = target / f"{record['run_at'].replace(':', '-')}.json"
    destination.write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return destination
