"""The gate rejects, retries once, and never calls an unparsed reply a pass."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import yaml
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.constants import TAG_NOSTREAM
from pydantic import ValidationError

from papyri_backend.verification import ReviewerMiddleware
from papyri_backend.verification.verdict import ReviewVerdict

_CONFIG = (
    Path(__file__).resolve().parents[1]
    / "configs"
    / "langchain_agent_with_review_loop.yaml"
)


class FakeReviewModel:
    """A chat model that returns fixed replies and counts its invocations.

    Its structured-output wrapper validates each reply against the schema the
    way the real one does: a reply that fits comes back parsed, one that does
    not comes back with ``parsed=None``.
    """

    model_name = "fake-reviewer"

    def __init__(self, *replies: str) -> None:
        self.replies = list(replies)
        self.calls: list[list[Any]] = []
        self.configs: list[Any] = []
        self.structured: list[dict[str, Any]] = []

    def with_structured_output(self, schema: Any, **kwargs: Any) -> Any:
        self.structured.append({"schema": schema, **kwargs})
        return SimpleNamespace(invoke=lambda messages, config=None: self._reply(
            schema, messages, config
        ))

    def _reply(self, schema: Any, messages: list[Any], config: Any) -> dict[str, Any]:
        self.calls.append(messages)
        self.configs.append(config)
        reply = self.replies.pop(0) if self.replies else '{"verdict": "pass"}'
        try:
            return {"raw": reply, "parsed": schema.model_validate_json(reply)}
        except ValidationError as exc:
            return {"raw": reply, "parsed": None, "parsing_error": exc}


class FailingModel:
    model_name = "unreachable"

    def with_structured_output(self, schema: Any, **kwargs: Any) -> Any:
        return self

    def invoke(self, messages: list[Any], config: Any = None) -> Any:
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


_SETTING_KEYS = (
    "system_prompt",
    "request_template",
    "evidence_start",
    "evidence_end",
    "critique_template",
    "critique_name",
    "unspecified_problem",
    "max_evidence_chars",
    "max_retries",
)


def review_settings() -> dict[str, str]:
    """The reviewer's settings exactly as the shipped config carries them.

    Read with a plain yaml load rather than ``utils.load_config``, which also
    resolves ``${LLM_MODEL}`` and friends and would need credentials CI does
    not have. Using the real config rather than a stub means a missing or
    renamed key fails here instead of at container start.
    """
    config = yaml.safe_load(_CONFIG.read_text(encoding="utf-8"))
    kwargs = next(
        entry["kwargs"]
        for entry in config["middleware"]
        if "ReviewerMiddleware" in entry["type"]
    )
    return {key: kwargs[key] for key in _SETTING_KEYS}


def review_prompt() -> str:
    """The reviewer's system prompt as the shipped config carries it."""
    return review_settings()["system_prompt"]


def build(model: Any, **kwargs: Any) -> ReviewerMiddleware:
    return ReviewerMiddleware(model=model, **{**review_settings(), **kwargs})


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
    # The prompt lives in the yaml and the schema lives in verdict.py, so
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
    assert critique.name == review_settings()["critique_name"]
    assert "Overstated." in critique.text


def test_the_retry_budget_is_spent_only_once() -> None:
    model = FakeReviewModel('{"verdict": "fail", "problems": ["Still wrong."]}')
    state = turn("Fishing was common.", evidence="8823")
    state["review_retries"] = 1

    update = build(model, max_retries=1).after_model(state, None)

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
        -1, HumanMessage("A reviewer rejected it: ...", name=review_settings()["critique_name"])
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


def test_the_review_call_is_kept_out_of_the_message_stream() -> None:
    """Without the tag the verdict JSON reaches the user instead of the answer.

    The reviewer's own reply is a model message carrying no tool calls, which is
    exactly the shape the caller reads as the turn's answer. Nothing else fails
    when the tag is missing: the verdict is still correct and the report is
    still written, so only the user sees the damage.
    """
    model = FakeReviewModel('{"verdict": "pass", "problems": []}')

    build(model=model).after_model(turn("Two documents mention Sarapion."), None)

    assert TAG_NOSTREAM in model.configs[0]["tags"]



def test_a_template_without_the_evidence_placeholder_fails_at_startup() -> None:
    with pytest.raises(ValueError, match="evidence"):
        build(FakeReviewModel(), request_template="QUESTION\n{question}\n{answer}")


def test_an_empty_evidence_marker_fails_at_startup() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        build(FakeReviewModel(), evidence_end="  ")


def test_a_critique_template_without_the_problems_placeholder_fails_at_startup() -> None:
    with pytest.raises(ValueError, match="problems"):
        build(FakeReviewModel(), critique_template="Rewrite your answer.")


def test_a_non_positive_evidence_limit_fails_at_startup() -> None:
    with pytest.raises(ValueError, match="max_evidence_chars"):
        build(FakeReviewModel(), max_evidence_chars=0)


def test_an_empty_critique_name_fails_at_startup() -> None:
    with pytest.raises(ValueError, match="critique_name"):
        build(FakeReviewModel(), critique_name=" ")


def test_a_negative_retry_budget_fails_at_startup() -> None:
    with pytest.raises(ValueError, match="max_retries"):
        build(FakeReviewModel(), max_retries=-1)


def test_only_this_turns_evidence_reaches_the_reviewer() -> None:
    model = FakeReviewModel()
    earlier = turn("Three do.", evidence="EARLIER-RESULT")["messages"]
    later = turn("Two do.", evidence="LATER-RESULT")["messages"]

    build(model).after_model({"messages": earlier + later, "review_retries": 0}, None)

    request = model.calls[0][1].content
    assert "LATER-RESULT" in request
    assert "EARLIER-RESULT" not in request


def test_evidence_from_before_a_critique_still_counts_for_the_rewrite() -> None:
    model = FakeReviewModel()
    state = turn("Fishing was common.", evidence="8823")
    name = review_settings()["critique_name"]
    state["messages"] += [
        HumanMessage("A reviewer rejected it: ...", name=name),
        AIMessage("Fishing is attested in one document."),
    ]

    build(model).after_model(state, None)

    assert "8823" in model.calls[0][1].content


def test_the_reviewer_is_called_with_the_verdict_schema() -> None:
    model = FakeReviewModel()

    build(model)

    assert model.structured == [
        {"schema": ReviewVerdict, "method": "json_schema", "include_raw": True}
    ]


def test_a_verdict_outside_pass_and_fail_is_unverified_not_a_pass() -> None:
    # The old text parser counted anything but exactly "fail" as a pass.
    model = FakeReviewModel('{"verdict": "failed", "problems": ["Overstated."]}')

    update = build(model).after_model(turn("Three do.", evidence="8823"), None)

    assert update["review_report"]["verdict"] == "unverified"
    assert "jump_to" not in update


def test_an_empty_unspecified_problem_fails_at_startup() -> None:
    with pytest.raises(ValueError, match="unspecified_problem"):
        build(FakeReviewModel(), unspecified_problem="")


def test_a_rejection_without_problems_sends_the_configured_problem() -> None:
    model = FakeReviewModel('{"verdict": "fail", "problems": []}')

    update = build(model).after_model(turn("Three do.", evidence="8823"), None)

    assert review_settings()["unspecified_problem"] in update["messages"][0].text
