"""Provide a connector for deepagents agents driven by LangGraph's v3 event stream."""

import json
import re
import uuid
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, get_args

from deepagents import create_deep_agent
from deepagents.middleware.filesystem import FilesystemOperation
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from .exceptions import InvalidDecision, StaleDecision
from .utils import utils

# Models that reason inline mark the trace as ordinary answer text instead of
# emitting reasoning events. The tags are matched leniently because whitespace
# and casing vary between deployments.
_THINK_OPEN = re.compile(r"<\s*think\s*>", re.IGNORECASE)
_THINK_CLOSE = re.compile(r"</\s*think\s*>", re.IGNORECASE)
_EMPTY_ANSWER_MESSAGE = "No answer was produced. Please try again."


def split_think(text: str) -> tuple[str, str]:
    """Separate an inline reasoning trace from the answer text.

    Args:
        text: One model message's text.

    Returns:
        The reasoning trace and the answer. The trace is empty when the message
        carries none.
    """
    # The trace always comes first, so the closing tag is the single point at
    # which the message switches from reasoning to answer.
    close_tag = _THINK_CLOSE.search(text)
    if close_tag is None:
        return "", text

    # Deployments whose chat template pre-fills the opening tag start the trace
    # without one, so its absence is not a reason to skip the split.
    reasoning = _THINK_OPEN.sub("", text[: close_tag.start()], 1)
    return reasoning, text[close_tag.end() :]


def split_streamed_think(
    text: str, *, assume_prefilled: bool = False
) -> tuple[str, str]:
    """Classify partial inline reasoning before its closing tag arrives.

    ``assume_prefilled`` is for reasoning models whose chat template consumes
    the opening ``<think>`` tag. Their output must be treated as reasoning from
    its first token; otherwise it briefly streams as answer text and jumps into
    the reasoning panel only when the closing tag arrives.
    """
    if _THINK_CLOSE.search(text) is not None:
        return split_think(text)

    open_tag = _THINK_OPEN.search(text)
    if open_tag is not None and not text[: open_tag.start()].strip():
        return text[open_tag.end() :], ""

    if assume_prefilled:
        return text, ""

    return "", text


@dataclass
class TurnOutput:
    """What one turn produced, as the client will read it."""

    answer: str = ""
    reasoning: str = ""
    error: str = ""

    def add_tool_calls(self, tool_calls: list[dict[str, Any]]) -> None:
        """Add finalized tool calls to the reasoning trace."""
        for tool_call in tool_calls or []:
            args = tool_call.get("args") or {}
            body = "\n".join(f"{k}: {v}" for k, v in args.items())
            self.reasoning += (
                f"\n\n````\nUsing tool: {tool_call.get('name')}\n{body}\n````\n\n"
            )

    def as_update(
        self, *, done: bool, interrupt: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Render a cumulative snapshot for an HTTP response stream."""
        if done:
            answer = self.as_answer(interrupt)
        else:
            answer = {
                "text": self.error or self.answer,
                "reasoning": self.reasoning,
                "interrupt": None,
            }
        return {**answer, "done": done}

    def as_answer(self, interrupt: dict[str, Any] | None) -> dict[str, Any]:
        """Render the turn as the chat response.

        Args:
            interrupt: The interrupt the run is now paused on, if any.

        Returns:
            The turn's ``text``, ``reasoning`` and ``interrupt``. A completed,
            uninterrupted turn without answer text receives a recoverable
            fallback message.
        """
        # A run that failed leaves no usable answer, so the error takes its
        # place rather than trailing whatever was emitted before the failure.
        text = self.error.strip() or self.answer.strip()
        if not text and interrupt is None:
            text = _EMPTY_ANSWER_MESSAGE

        return {
            "text": text,
            "reasoning": self.reasoning.strip(),
            "interrupt": interrupt,
        }


class LangChainAgent:
    """Connect to a deepagents agent and stream its events."""

    @classmethod
    def from_config(cls, path: str | Path) -> "LangChainAgent":
        """Build an agent from a yaml config file.

        Args:
            path: Path to the config file, whose keys are the arguments below.

        Returns:
            The configured agent.
        """
        return cls(**utils.load_config(path))

    def __init__(self, *, inline_reasoning: bool | None = None, **agent_kwargs: Any):
        """Build a deep agent.

        Args:
            inline_reasoning: Treat untagged text before ``</think>`` as a
                reasoning trace. When omitted, Qwen models are detected by
                name; set it explicitly for other model families.
            agent_kwargs: Keyword arguments for ``create_deep_agent``, such as
                ``model``, ``tools``, ``system_prompt`` and ``interrupt_on``.
                Nested ``{"type": ..., "kwargs": {...}}`` entries are
                constructed. A ``checkpointer`` is added when none is supplied.
        """
        agent_kwargs.setdefault(
            "checkpointer", InMemorySaver()
        )  # TODO: make the checkpointer configurable

        # The model is built first so that it can be offered to the middlewares
        # that run a model of their own. Building everything in one pass would
        # instead offer the model to its own constructor.
        model = utils.build(agent_kwargs.get("model"))
        model_name = getattr(model, "model_name", None) or getattr(model, "model", "")
        self.inline_reasoning = (
            "qwen" in str(model_name).lower()
            if inline_reasoning is None
            else inline_reasoning
        )
        agent_kwargs = {
            key: value if key == "model" else utils.build(value, {"model": model})
            for key, value in agent_kwargs.items()
        }
        agent_kwargs["model"] = model

        self.agent = create_deep_agent(**agent_kwargs)
        self._verify_config(agent_kwargs)
        self.thread_id = str(uuid.uuid4())

    def _verify_config(self, agent_kwargs: Mapping[str, Any]) -> None:
        """Check that names in the config refer to things that exist, e.g., agent tools

        Args:
            agent_kwargs: The keyword arguments the agent was built from.

        Raises:
            ValueError: A tool or operation named in the config does not exist.
        """
        # A misnamed key here is silent: it matches nothing, so it neither fires
        # nor errors, and the guard the config asks for is simply absent.
        tool_names = set(self.agent.nodes["tools"].bound.tools_by_name)
        unknown_tools = sorted(set(agent_kwargs.get("interrupt_on") or {}) - tool_names)
        if unknown_tools:
            raise ValueError(
                f"interrupt_on names tools the agent does not have: {unknown_tools}. "
                f"Available tools: {sorted(tool_names)}"
            )

        operations = set(get_args(FilesystemOperation))
        for permission in agent_kwargs.get("permissions") or []:
            unknown_ops = sorted(
                set(getattr(permission, "operations", ())) - operations
            )
            if unknown_ops:
                raise ValueError(
                    f"permission names operations that do not exist: {unknown_ops}. "
                    f"Available operations: {sorted(operations)}. Note these are "
                    f"filesystem operations, not tool names."
                )

    @property
    def _config(
        self,
    ) -> dict[str, Any]:  # TODO: why is this needed, I am not sure this does much
        """Return the runnable config binding a run to the current thread.

        Returns:
            A config carrying the thread id the checkpointer keys state on.
        """
        return {"configurable": {"thread_id": self.thread_id}}

    def _pending_interrupt(self):
        """Return the interrupt the run is paused on, if any.

        The checkpointer is the single source of truth here rather than the
        retained run, because a pause outlives the request that produced it.

        Returns:
            The pending ``Interrupt``, or ``None`` when nothing is paused.
        """
        interrupts = self.agent.get_state(self._config).interrupts
        return interrupts[0] if interrupts else None

    @staticmethod
    def _interrupt_view(interrupt) -> dict[str, Any]:
        """Describe a pending interrupt for a client that has to answer it.

        Args:
            interrupt: The ``Interrupt`` the run is paused on.

        Returns:
            The interrupt's id and one entry per paused action, carrying the
            action's name, the arguments the model asked for, and the decisions
            allowed for that action specifically.
        """
        request = interrupt.value
        return {
            "id": interrupt.id,
            "actions": [
                {
                    "name": action["name"],
                    "args": action.get("args") or {},
                    "allowed_decisions": list(config["allowed_decisions"]),
                }
                for action, config in zip(
                    request["action_requests"], request["review_configs"]
                )
            ],
        }

    def _resume_command(self, payload: Mapping[str, Any]) -> Command:
        """Turn a decision reply into the command that resumes the paused run.

        The graph raises ``ValueError`` for a decision count that does not match
        the paused actions, or for a type the action does not allow. Both are
        checked here instead, so a bad reply is a rejected request rather than a
        failed run.

        Args:
            payload: A decision reply, carrying ``interrupt_id`` and one entry in
                ``decisions`` per paused action, in the same order.

        Returns:
            The command that resumes the run with those decisions.

        Raises:
            StaleDecision: Nothing is paused, or the reply names another interrupt.
            InvalidDecision: The reply has the wrong number of decisions, or one
                the action does not allow.
        """
        interrupt = self._pending_interrupt()
        if interrupt is None:
            raise StaleDecision("No decision is pending.")

        if payload.get("interrupt_id") != interrupt.id:
            raise StaleDecision(
                "This decision answers an interrupt that is no longer pending."
            )

        request = interrupt.value
        action_requests = request["action_requests"]
        review_configs = request["review_configs"]
        replies = payload.get("decisions") or []

        if len(replies) != len(action_requests):
            raise InvalidDecision(
                f"Expected {len(action_requests)} decisions, got {len(replies)}."
            )

        decisions = [
            self._build_decision(reply, action, config)
            for reply, action, config in zip(replies, action_requests, review_configs)
        ]

        return Command(resume={"decisions": decisions})

    @staticmethod
    def _build_decision(
        reply: Mapping[str, Any],
        action: Mapping[str, Any],
        config: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Translate one client reply into the decision the middleware expects.

        The edited action's name is taken from the paused action rather than from
        the reply, so a client cannot redirect a decision at a different tool.

        Args:
            reply: One entry of the client's ``decisions`` list.
            action: The paused action the reply answers.
            config: That action's review policy.

        Returns:
            A decision payload for ``HumanInTheLoopMiddleware``.

        Raises:
            InvalidDecision: The type is missing, not allowed for this action, or
                carries the wrong body for its kind.
        """
        decision_type = reply.get("type")
        allowed = config["allowed_decisions"]

        if decision_type not in allowed:
            raise InvalidDecision(
                f"Decision '{decision_type}' is not allowed for "
                f"'{action['name']}'. Expected one of {list(allowed)}."
            )
        if decision_type == "approve":
            return {"type": "approve"}

        if decision_type == "edit":
            args = reply.get("args")
            if not isinstance(args, dict):
                raise InvalidDecision("An edited action needs its args as an object.")
            return {
                "type": "edit",
                "edited_action": {"name": action["name"], "args": args},
            }

        if decision_type == "reject":
            message = (reply.get("message") or "").strip()
            return (
                {"type": "reject", "message": message}
                if message
                else {"type": "reject"}
            )

        message = (reply.get("message") or "").strip()
        if not message:
            raise InvalidDecision("Responding on behalf of a tool needs a message.")
        return {"type": "respond", "message": message}

    def _stream_drive(self, payload: Any, turn: TurnOutput) -> Iterator[dict[str, Any]]:
        """Drive one graph run and yield cumulative output after every delta."""

        # LangGraph's v3 ``messages`` projection contains one live stream per
        # model call. Iterating its raw events keeps reasoning and text in
        # provider order; converting either typed projection directly to ``str``
        # would first drain it and lose HTTP streaming.

        run = self.agent.stream_events(payload, config=self._config, version="v3")
        for message in run.messages:
            answer_before_message = turn.answer
            reasoning_before_message = turn.reasoning
            streamed_text = ""
            streamed_reasoning = ""
            for kind, delta in self._message_deltas(message):
                if kind == "reasoning":
                    streamed_reasoning += delta
                else:
                    streamed_text += delta

                # Inline <think> models report their trace through the text
                # projection. Re-evaluating the current model message on each
                # delta also handles a closing tag split across chunks. A
                # separately reported reasoning stream makes the text
                # projection unambiguously answer text.
                if streamed_reasoning:
                    inline_reasoning, answer = "", streamed_text
                else:
                    inline_reasoning, answer = split_streamed_think(
                        streamed_text,
                        assume_prefilled=getattr(self, "inline_reasoning", False),
                    )
                turn.answer = answer_before_message + answer
                turn.reasoning = (
                    reasoning_before_message + streamed_reasoning + inline_reasoning
                )
                yield turn.as_update(done=False)

            tool_calls = message.tool_calls.get()
            if tool_calls:
                turn.add_tool_calls(tool_calls)
                yield turn.as_update(done=False)

    @staticmethod
    def _message_deltas(message: Any) -> Iterator[tuple[str, str]]:
        """Yield interleaved reasoning/text deltas from one model message.

        Real v3 message streams expose their raw protocol events through
        iteration. Consuming those events preserves provider order, unlike
        draining the reasoning and text projections one after another. The
        projection fallback keeps lightweight graph fakes and transitional
        stream implementations compatible.
        """
        try:
            events = iter(message)
        except TypeError:
            for delta in message.reasoning:
                yield "reasoning", str(delta)
            for delta in message.text:
                yield "text", str(delta)
            return

        for event in events:
            if event.get("event") != "content-block-delta":
                continue
            delta = event.get("delta") or event.get("content_block") or {}
            delta_type = delta.get("type")
            if delta_type == "reasoning-delta":
                text = delta.get("reasoning", "")
                if text:
                    yield "reasoning", str(text)
            elif delta_type == "text-delta":
                text = delta.get("text", "")
                if text:
                    yield "text", str(text)
            elif delta_type == "reasoning":
                text = delta.get("reasoning", "")
                if text:
                    yield "reasoning", str(text)
            elif delta_type == "text":
                text = delta.get("text", "")
                if text:
                    yield "text", str(text)

    @staticmethod
    def _as_decision(text: str) -> dict[str, Any] | None:
        """Read a message as a decision reply, if that is what it is.

        Decisions travel as the JSON text of an ordinary user message, so every
        message is examined. ``interrupt_id`` is what marks one, because it is
        specific enough that ordinary prose cannot produce it by accident.

        Args:
            text: The incoming message's text.

        Returns:
            The decision payload, or ``None`` for an ordinary message.
        """
        stripped = text.strip()
        if not stripped.startswith("{"):
            return None

        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            return None

        if isinstance(payload, dict) and "interrupt_id" in payload:
            return payload
        return None

    def stream_single_turn(self, message) -> Iterator[dict[str, Any]]:
        """Stream one turn as cumulative text/reasoning snapshots.

        Decision validation happens before the iterator is returned. This is
        important for HTTP: stale or invalid decisions can still receive their
        409/422 status before streaming response headers have been sent.
        """
        text = message["content"][0]["text"]
        decision = self._as_decision(text)

        if decision is not None:
            # Raised before the run is touched, so a refused decision leaves
            # the graph paused exactly as it was.
            payload = self._resume_command(decision)
        else:
            payload = {"messages": [{"role": "user", "content": text}]}

        return self._stream_prepared_turn(payload)

    def _stream_prepared_turn(self, payload: Any) -> Iterator[dict[str, Any]]:
        turn = TurnOutput()

        try:
            yield from self._stream_drive(payload, turn)
        except Exception as exc:
            # Run failures deliberately travel as chat output during local
            # development. Because updates are cumulative, this terminal
            # snapshot replaces any incomplete answer already shown.
            turn.error = f"The agent run failed: {exc}"

        interrupt = self._pending_interrupt()
        interrupt_view = None
        if interrupt is not None:
            turn.answer += "Please decide how you want to proceed:\n"
            interrupt_view = self._interrupt_view(interrupt)

        yield turn.as_update(done=True, interrupt=interrupt_view)
