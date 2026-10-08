"""Run the question set against the real agent and write one run record.

    set -a; source ../.env; set +a      # VPN if off campus
    .venv/bin/python scripts/evaluate_grounding.py

Honours the same ``AGENT_CONFIG`` the server uses, so the evaluation exercises
whatever the app would actually load. ``EVALUATION_QUESTIONS`` and
``EVALUATION_OUTPUT`` override the question set and where records are kept.

Needs the database and the model endpoint. A session is started per question so
each one begins with an empty conversation; that costs a reconnect and an agent
rebuild per question, which is the price of the runs being comparable.
"""

import os
from pathlib import Path

from papyri_backend import session
from papyri_backend.evaluation import (
    build_record,
    load_questions,
    run_question,
    summarise,
    write_record,
)
from papyri_backend.settings import load_environment

_ROOT = Path(__file__).resolve().parent.parent

if __name__ == "__main__":
    load_environment()

    questions_file = Path(
        os.getenv("EVALUATION_QUESTIONS", _ROOT / "evaluation" / "questions.yaml")
    )
    config = os.getenv(
        "AGENT_CONFIG", str(_ROOT / "configs" / "langchain_agent_with_review_loop.yaml")
    )
    output = Path(os.getenv("EVALUATION_OUTPUT", _ROOT / "evaluation" / "runs"))

    questions = load_questions(questions_file)
    print(f"{len(questions)} questions, config {config}\n")

    results = []
    try:
        for question in questions:
            # A fresh session is a fresh agent on a fresh thread, which is how
            # chat.py's /new resets a conversation.
            current = session.start()
            result = run_question(current.agent, question["text"])
            result |= {"id": question["id"], "category": question.get("category")}
            results.append(result)
            print(
                f"{result['id']:<20} {result['verdict']:<11} "
                f"evidence={result['evidence_count']:<3} "
                f"links={result['links']:<3} rewrites={result['retries']} "
                f"{result['seconds']}s"
            )
    finally:
        session.clear()

    record = build_record(
        results=results,
        config=config,
        questions_file=str(questions_file),
    )
    destination = write_record(record, output)

    print()
    for name, value in summarise(results).items():
        print(f"{name:<18} {value}")
    print(f"\nWritten to {destination}")
