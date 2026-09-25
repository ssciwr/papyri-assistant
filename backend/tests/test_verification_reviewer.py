"""The gate rejects, retries once, and never calls an unparsed reply a pass."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import yaml
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from papyri_backend.verification import ReviewerMiddleware
from papyri_backend.verification.reviewer import CRITIQUE_NAME

_CONFIG = (
    Path(__file__).resolve().parents[1]
    / "configs"
    / "langchain_agent_with_review_loop.yaml"
)


class FakeReviewModel:
    """A chat model that returns fixed replies and counts its invocations."""

    model_name = "fake-reviewer"

    def __init__(self, *replies: str) -> None:
        self.replies = list(replies)
        self.calls: list[list[Any]] = []

    def invoke(self, messages: list[Any]) -> Any:
        self.calls.append(messages)
        reply = self.replies.pop(0) if self.replies else '{"verdict": "pass"}'
        return SimpleNamespace(text=reply, content=reply)


class FailingModel:
    model_name = "unreachable"

    def invoke(self, messages: list[Any]) -> Any:
        raise RuntimeError("review endpoint unreachable")


def turn(answer: str, *, evidence: str | None = None) -> dict[str, Any]:
    """A finished turn: a question, an optional tool round trip, an answer."""
    messages: list[Any] = [HumanMessage("Which documents mention Sarapion?")]
    if evidence is not None:
        messages.append(
            AIMessage(
                "",
                tool_calls=[
                    {"id": "c1", "name": "similarity_search", "args": {"query": "S"}}
                ],
            )
        )
        messages.append(ToolMessage(evidence, tool_call_id="c1"))
    messages.append(AIMessage(answer))
    return {"messages": messages, "review_retries": 0}


def review_prompt() -> str:
    """The reviewer's prompt exactly as the shipped config carries it.

    Read with a plain yaml load rather than ``utils.load_config``, which also
    resolves ``${LLM_MODEL}`` and friends and would need credentials CI does
    not have. Using the real prompt rather than a stub means a missing or
    renamed key fails here instead of at container start.
    """
    config = yaml.safe_load(_CONFIG.read_text(encoding="utf-8"))
    return next(
        entry["kwargs"]["system_prompt"]
        for entry in config["middleware"]
        if "ReviewerMiddleware" in entry["type"]
    )


def build(model: Any, **kwargs: Any) -> ReviewerMiddleware:
    kwargs.setdefault("system_prompt", review_prompt())
    return ReviewerMiddleware(model=model, **kwargs)


def test_nothing_is_reviewed_while_the_agent_is_still_calling_tools() -> None:
    model = FakeReviewModel()
    state = {
        "messages": [
            HumanMessage("q"),
            AIMessage(
                "looking", tool_calls=[{"id": "c1", "name": "query_sql", "args": {}}]
            ),
        ]
    }

    assert build(model).after_model(state, None) is None
    assert model.calls == []


def test_an_empty_final_message_is_not_reviewed() -> None:
    model = FakeReviewModel()
    state = {"messages": [HumanMessage("q"), AIMessage("   ")]}

    assert build(model).after_model(state, None) is None
    assert model.calls == []


def test_a_passing_answer_is_released_with_its_report() -> None:
    model = FakeReviewModel('{"verdict": "pass", "problems": []}')

    update = build(model).after_model(turn("Three do.", evidence="8823"), None)

    assert update == {
        "review_report": {
            "retries": 0,
            "evidence_count": 1,
            "model": "fake-reviewer",
            "verdict": "pass",
            "problems": [],
            "parsed": True,
        }
    }


def test_the_configured_prompt_is_what_the_reviewer_is_sent() -> None:
    # The prompt lives in the yaml and the parser lives in verdict.py, so
    # nothing else would notice if the config key were renamed away.
    model = FakeReviewModel('{"verdict": "pass", "problems": []}')

    build(model).after_model(turn("Three do.", evidence="8823"), None)

    assert model.calls[0][0].content == review_prompt()


def test_a_rejected_answer_is_sent_back_with_the_critique() -> None:
    model = FakeReviewModel('{"verdict": "fail", "problems": ["Overstated."]}')

    update = build(model).after_model(turn("Fishing was common.", evidence="8823"), None)

    assert update["jump_to"] == "model"
    assert update["review_retries"] == 1
    critique = update["messages"][0]
    assert critique.name == CRITIQUE_NAME
    assert "Overstated." in critique.text


def test_the_retry_budget_is_spent_only_once() -> None:
    model = FakeReviewModel('{"verdict": "fail", "problems": ["Still wrong."]}')
    state = turn("Fishing was common.", evidence="8823")
    state["review_retries"] = 1

    update = build(model).after_model(state, None)

    assert "jump_to" not in update
    assert update["review_report"]["verdict"] == "fail"


def test_an_unparseable_reply_is_unverified_and_never_a_pass() -> None:
    model = FakeReviewModel("I think it reads well enough.")

    update = build(model).after_model(turn("Three do.", evidence="8823"), None)

    report = update["review_report"]
    assert report["verdict"] == "unverified"
    assert report["parsed"] is False
    assert "jump_to" not in update


def test_an_unreachable_reviewer_degrades_to_no_review() -> None:
    update = build(FailingModel()).after_model(turn("Three do.", evidence="8823"), None)

    report = update["review_report"]
    assert report["verdict"] == "skipped"
    assert "unreachable" in report["error"]


def test_the_question_reviewed_is_the_users_not_the_critique() -> None:
    model = FakeReviewModel('{"verdict": "pass", "problems": []}')
    state = turn("Three do.", evidence="8823")
    state["messages"].insert(
        -1, HumanMessage("A reviewer rejected it: ...", name=CRITIQUE_NAME)
    )

    build(model).after_model(state, None)

    request = model.calls[0][1].text
    assert "Which documents mention Sarapion?" in request
    assert "A reviewer rejected it" not in request


def test_the_hook_is_declared_able_to_jump_back_to_the_model() -> None:
    """Without this, ``jump_to`` is silently ignored: the critique is injected,
        the turn ends, and the first answer ships. No error, no warning.

        ``__can_jump_to__`` is where ``hook_config`` stores it, verified against the
        installed langchain 1.3.18.
        """
    declared = getattr(ReviewerMiddleware.after_model, "__can_jump_to__", None)

    assert declared is not None, "after_model has lost its @hook_config decorator"
    assert "model" in declared