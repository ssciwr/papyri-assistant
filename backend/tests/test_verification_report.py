"""The verification report is rendered as plain reasoning text."""

from __future__ import annotations

from papyri_backend.verification import format_report


def test_a_passing_report_shows_verdict_and_counts() -> None:
    text = format_report(
        {"verdict": "pass", "evidence_count": 2, "retries": 0, "problems": []}
    )

    assert "Verification\nverdict: pass\nevidence items: 2\nrewrites: 0\n" in text


def test_a_failing_report_lists_each_problem() -> None:
    text = format_report({"verdict": "fail", "problems": ["Overstated.", "No link."]})

    assert "- Overstated.\n- No link." in text


def test_an_unreadable_reply_is_called_unverified() -> None:
    text = format_report({"verdict": "unverified", "parsed": False})

    assert "could not be read, so this answer is unverified" in text


def test_an_unreachable_reviewer_is_reported_with_its_error() -> None:
    text = format_report({"verdict": "skipped", "error": "timeout"})

    assert "reviewer unavailable: timeout" in text
