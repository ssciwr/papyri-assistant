"""The gate between the agent's answer and the user.

One model pass, no tools, over the question, the answer and everything the
agent retrieved this turn. It answers closed questions about text already in
front of it -- a much easier task than answering the original question -- and
can send the answer back for a rewrite up to ``max_retries`` times.

The reviewer's prompt lives in the agent config beside the agent's own, so it
can be tuned without touching Python. There is no check in code that the agent
consulted the corpus at all: an answer that makes factual claims without any
tool calls is caught only by a rule in that prompt.
"""

from __future__ import annotations

from typing import Any, NotRequired

from langchain.agents.middleware import AgentMiddleware, AgentState, hook_config
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.constants import TAG_NOSTREAM

from .evidence import evidence_blocks
from .request import REQUEST_PLACEHOLDERS, build_review_request
from .verdict import ReviewVerdict, read_verdict


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
        request_template: str,
        evidence_start: str,
        evidence_end: str,
        critique_template: str,
        critique_name: str,
        unspecified_problem: str,
        max_evidence_chars: int,
        max_retries: int,
    ) -> None:
        """Build the gate.

        Args:
            model: The chat model the reviewer runs on
            system_prompt: The reviewer's instructions, from the agent config.
            request_template: The layout of the message the reviewer judges,
                with ``{question}``, ``{answer}`` and ``{evidence}``
                placeholders, from the agent config.
            evidence_start: The line that opens the evidence fence.
            evidence_end: The line that closes the evidence fence.
            critique_template: The message the agent gets when its answer
                is rejected, with a ``{problems}`` placeholder, from the
                agent config.
            critique_name: The name stamped on the critique message, so it
                is not mistaken for the user's question, from the agent
                config.
            unspecified_problem: The problem given to a rejection that names
                none, so the agent still has something to fix, from the agent
                config.
            max_evidence_chars: Longest tool result shown per evidence
                item, from the agent config.
            max_retries: How many times a rejected answer may be sent back for
                a rewrite, from the agent config.

        Raises:
            ValueError: If a template lacks a placeholder, a marker, the
                critique name or the unspecified problem is empty, the evidence limit is not positive, or
                max_retries is negative, so a broken config fails at startup,
                not mid-turn.
        """
        missing = [p for p in REQUEST_PLACEHOLDERS if p not in request_template]
        if missing:
            raise ValueError(f"request_template is missing {', '.join(missing)}")
        if not evidence_start.strip() or not evidence_end.strip():
            raise ValueError("evidence_start and evidence_end must not be empty")
        if "{problems}" not in critique_template:
            raise ValueError("critique_template is missing {problems}")
        if not critique_name.strip():
            raise ValueError("critique_name must not be empty")
        if not unspecified_problem.strip():
            raise ValueError("unspecified_problem must not be empty")
        if max_evidence_chars < 1:
            raise ValueError("max_evidence_chars must be at least 1")
        if max_retries < 0:
            raise ValueError("max_retries must not be negative")
        super().__init__()
        self.model = model
        # The server returns the verdict in this shape, so it never has to be
        # parsed out of free text. include_raw keeps a reply that does not fit
        # from raising: it comes back with parsed=None and is reported as
        # unverified, while an unreachable endpoint still raises below.
        self.reviewer = model.with_structured_output(
            ReviewVerdict, method="json_schema", include_raw=True
        )
        self.system_prompt = system_prompt
        self.request_template = request_template
        self.evidence_start = evidence_start
        self.evidence_end = evidence_end
        self.critique_template = critique_template
        self.critique_name = critique_name
        self.unspecified_problem = unspecified_problem
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

        question, turn = _current_turn(messages, self.critique_name)
        evidence = evidence_blocks(turn, max_chars=self.max_evidence_chars)
        retries = state.get("review_retries", 0)
        report: dict[str, Any] = {
            "retries": retries,
            "evidence_count": len(evidence),
            "model": getattr(self.model, "model_name", None),
        }

        request = build_review_request(
            template=self.request_template,
            evidence_start=self.evidence_start,
            evidence_end=self.evidence_end,
            question=question,
            answer=answer,
            evidence=evidence,
        )
        try:
            reply = self.reviewer.invoke(
                [SystemMessage(self.system_prompt), HumanMessage(request)],
                # Keep this call out of the graph's message stream. Without the
                # tag the reviewer's own reply is streamed as a model message
                # with no tool calls, which the caller reads as the turn's
                # answer: the verdict JSON reaches the user and the real answer
                # is lost. See langgraph/pregel/_messages.py.
                config={"tags": [TAG_NOSTREAM]},
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

        verdict = read_verdict(reply, unspecified_problem=self.unspecified_problem)
        # An unparseable reply is neither a pass nor a fail.
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
                    self.critique_template.format(problems=critique),
                    name=self.critique_name,
                )
            ],
            "jump_to": "model",
        }


def _current_turn(messages: list[Any], critique_name: str) -> tuple[str, list[Any]]:
    """Return the user's latest question and the messages that followed it.

    The message list holds the whole conversation, but only this turn's tool
    results are evidence for this turn's answer. A critique this gate injected
    is skipped when looking for the question: after a retry the newest human
    message is the critique, and the evidence gathered before it still counts.
    """
    for index in range(len(messages) - 1, -1, -1):
        message = messages[index]
        if getattr(message, "type", None) != "human":
            continue
        if getattr(message, "name", None) == critique_name:
            continue
        return _text_of(message), messages[index + 1 :]
    return "", messages


def _text_of(message: Any) -> str:
    """Return a message's text whatever shape its content arrived in."""
    text = getattr(message, "text", None)
    if isinstance(text, str):
        return text
    content = getattr(message, "content", "")
    return content if isinstance(content, str) else str(content)