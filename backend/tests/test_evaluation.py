"""The evaluation harness, with no model, no database and no network.

What is covered here is the measurement itself: reading a turn's events, and the
one piece of summary arithmetic whose rule is not obvious from reading it. The
rest of the module is exercised by running ``scripts/evaluate_grounding.py``,
where a mistake is visible in the output rather than silent.
"""

from __future__ import annotations

from typing import Any

from papyri_backend.evaluation import run_question, summarise

LINK = "https://papyri.info/editions/p.zen.pestm/54"


class FakeAgent:
    """An agent that replays a fixed event stream for one turn."""

    def __init__(self, events: list[dict[str, Any]]) -> None:
        self.events = events
        self.asked: list[str] = []

    def stream_single_turn(self, message: dict[str, Any]) -> list[dict[str, Any]]:
        self.asked.append(message["content"][0]["text"])
        return self.events


def result(**overrides: Any) -> dict[str, Any]:
    base = {
        "parsed": True,
        "retries": 0,
        "verdict": "pass",
        "seconds": 1.0,
    }
    return base | overrides


# --- reading one turn -------------------------------------------------------


def test_a_turn_is_read_into_answer_links_and_verdict() -> None:
    agent = FakeAgent(
        [
            {"type": "reasoning", "content": "Searching."},
            {"type": "text", "content": f"TM 1885 is a lease: [TM 1885]({LINK})."},
            {
                "type": "verification",
                "verification": {
                    "verdict": "pass",
                    "parsed": True,
                    "retries": 0,
                    "evidence_count": 2,
                    "problems": [],
                },
            },
            {"type": "done", "interrupt": None},
        ]
    )

    outcome = run_question(agent, "Find a lease.")

    assert agent.asked == ["Find a lease."]
    assert outcome["answer"].startswith("TM 1885 is a lease")
    assert outcome["links"] == 1
    assert outcome["verdict"] == "pass"
    assert outcome["evidence_count"] == 2
    assert outcome["seconds"] >= 0


def test_a_markdown_link_is_counted_without_its_closing_bracket() -> None:
    # The url is extracted for counting, so the regex must stop before ")".
    agent = FakeAgent(
        [{"type": "text", "content": f"See [TM 1885]({LINK}) and [again]({LINK})."}]
    )

    assert run_question(agent, "q")["links"] == 1


def test_a_turn_without_a_reviewer_is_marked_no_report() -> None:
    # Distinct from the reviewer's own "skipped": here no reviewer ran at all.
    agent = FakeAgent([{"type": "text", "content": "Two documents do."}])

    outcome = run_question(agent, "q")

    assert outcome["verdict"] == "no-report"
    assert outcome["parsed"] is None


# --- the summary ------------------------------------------------------------


def test_the_parse_rate_counts_only_turns_the_reviewer_judged() -> None:
    summary = summarise(
        [
            result(),
            result(parsed=False, verdict="unverified"),
            # Never reviewed, so it says nothing about the reviewer's format.
            result(parsed=None, verdict="no-report"),
        ]
    )

    assert summary["reviewed"] == 2
    assert summary["parse_rate"] == 0.5
    assert summary["unverified"] == 1
