"""Render the reviewer's report as text for the reasoning trace.

The report reaches the user as an ordinary reasoning message, so the frontend
shows it like any other step and does not need to know the reviewer exists.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def format_report(report: Mapping[str, Any]) -> str:
    """Turn a verification report into a block for the reasoning trace.

    Args:
        report: The ``review_report`` the reviewer middleware wrote.

    Returns:
        A fenced block with the verdict, the number of evidence items and
        rewrites, any reviewer malfunction, and the problems found.
    """
    lines = [
        f"verdict: {report.get('verdict')}",
        f"evidence items: {report.get('evidence_count', 0)}",
        f"rewrites: {report.get('retries', 0)}",
    ]
    if report.get("parsed") is False:
        lines.append(
            "the reviewer's reply could not be read, so this answer is unverified"
        )
    if report.get("error"):
        lines.append(f"reviewer unavailable: {report['error']}")
    lines += [f"- {problem}" for problem in report.get("problems", [])]
    body = "\n".join(lines)
    return f"\n\n```\nVerification\n{body}\n```\n\n"
