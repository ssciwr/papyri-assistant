"""The gate between the agent's answer and the user.

One model pass, no tools, over the question, the answer and everything the
agent retrieved this turn. It answers five closed questions about text already
in front of it -- a much easier task than answering the original question --
and can send the answer back exactly once.

The reviewer's prompt lives in the agent config beside the agent's own, so it
can be tuned without touching Python. Until the design's deterministic tier 1
checks exist, that prompt is the only thing enforcing that the agent consulted
the corpus at all.
"""

from __future__ import annotations

from typing import Any, NotRequired

from langchain.agents.middleware import AgentMiddleware, AgentState, hook_config
from langchain_core.messages import HumanMessage, SystemMessage

from .evidence import collect_evidence
from .request import build_review_request
from .verdict import parse_verdict

CRITIQUE_NAME = "reviewer"
"""Stamped on injected critiques so they are not mistaken for the question."""

_CRITIQUE_TEMPLATE = """A reviewer read your answer against the evidence you
retrieved and rejected it:

{problems}

Rewrite your answer to address every point. Retrieve more evidence first if you
need it. Do not defend the previous answer."""


class ReviewState(AgentState):
    """Adds the reviewer's per-turn bookkeeping to the agent state.

    Both live in graph state rather than on the middleware instance because one
    middleware object serves every thread in a process-global session; an
    instance attribute would leak one conversation's retry count into another's.
    """

    review_retries: NotRequired[int]
    review_report: NotRequired[dict[str, Any]]


class ReviewerMiddleware(AgentMiddleware):
    """Gate the agent's final answer on a second model's verdict."""

    state_schema = ReviewState

    def __init__(
        self,
        *,
        model: Any,
        system_prompt: str,
        max_retries: int = 1,
        max_evidence_chars: int = 4000,
    ) -> None:
        """Build the gate.

        Args:
            model: The chat model the reviewer runs on. Supplied automatically
                from the agent config: ``utils.build`` passes the already-built
                agent model to any middleware whose constructor names ``model``.
                Name a different one in the config's kwargs to review on a
                separate endpoint.
            system_prompt: The reviewer's instructions, from the agent config.
                Required rather than defaulted, so a missing key fails at
                startup instead of silently reviewing with stale text.
            max_retries: How many times a rejected answer may be sent back. The
                design specifies one. Zero records the verdict without acting on
                it, which is a useful way to observe the gate before it bites.
            max_evidence_chars: Longest tool result shown per evidence item.
        """
        super().__init__()
        self.model = model
        self.system_prompt = system_prompt
        self.max_retries = max_retries
        self.max_evidence_chars = max_evidence_chars

    def before_agent(self, state: Any, runtime: Any) -> dict[str, Any] | None:
        """Reset the retry budget at the start of each turn."""
        return {"review_retries": 0}

    @hook_config(can_jump_to=["model"])
    def after_model(self, state: Any, runtime: Any) -> dict[str, Any] | None:
        """Review the answer, if this model call produced one.

        Returns:
            ``None`` when there is nothing to review. Otherwise a state update
            carrying the verification report, plus the critique and ``jump_to``
            when the answer is rejected and budget remains.
        """
        messages = state["messages"]
        last = messages[-1] if messages else None

        # after_model fires after every model call, and most of them are tool
        # requests with no answer in them. Reviewing those would cost one full
        # model call per tool call.
        if last is None or getattr(last, "tool_calls", None):
            return None

        answer = _text_of(last).strip()
        if not answer:
            return None

        items = collect_evidence(messages, max_chars=self.max_evidence_chars)
        retries = state.get("review_retries", 0)
        report: dict[str, Any] = {
            "retries": retries,
            "evidence_count": len(items),
            "model": getattr(self.model, "model_name", None),
        }

        request = build_review_request(
            question=_question(messages), answer=answer, items=items
        )
        try:
            reply = self.model.invoke(
                [SystemMessage(self.system_prompt), HumanMessage(request)]
            )
        except Exception as exc:
            # The reviewer is an additional check, not a dependency. An
            # unreachable review endpoint must degrade to no review rather than
            # taking down a turn whose answer may be perfectly good.
            return {
                "review_report": {
                    **report,
                    "verdict": "skipped",
                    "problems": [],
                    "parsed": None,
                    "error": str(exc),
                }
            }

        verdict = parse_verdict(_text_of(reply))
        # An unparseable reply is neither a pass nor a fail. Calling it a pass
        # would let a formatting slip read as an endorsement.
        if not verdict.parsed:
            decision = "unverified"
        elif verdict.passed:
            decision = "pass"
        else:
            decision = "fail"

        report |= {
            "verdict": decision,
            "problems": list(verdict.problems),
            "parsed": verdict.parsed,
        }

        if verdict.passed or retries >= self.max_retries:
            return {"review_report": report}

        critique = "\n".join(f"- {problem}" for problem in verdict.problems)
        return {
            "review_report": report,
            "review_retries": retries + 1,
            "messages": [
                HumanMessage(
                    _CRITIQUE_TEMPLATE.format(problems=critique), name=CRITIQUE_NAME
                )
            ],
            "jump_to": "model",
        }


def _question(messages: list[Any]) -> str:
    """Return the user's question, ignoring any critique this gate injected.

    After a retry the newest human message is the critique, so reviewing
    against the last human message would review the answer against the
    reviewer's own complaint instead of against what the user asked.
    """
    for message in reversed(messages):
        if getattr(message, "type", None) != "human":
            continue
        if getattr(message, "name", None) == CRITIQUE_NAME:
            continue
        return _text_of(message)
    return ""


def _text_of(message: Any) -> str:
    """Return a message's text whatever shape its content arrived in."""
    text = getattr(message, "text", None)
    if isinstance(text, str):
        return text
    content = getattr(message, "content", "")
    return content if isinstance(content, str) else str(content)