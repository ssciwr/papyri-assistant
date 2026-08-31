"""Provide a connector for deepagents agents driven by LangGraph's v3 event stream."""

import json
import re
import uuid
from collections.abc import Mapping
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


@dataclass
class TurnOutput:
    """What one turn produced, as the client will read it."""

    answer: str = ""
    reasoning: str = ""
    error: str = ""

    def add_message(
        self, text: str, reasoning: str, tool_calls: list[dict[str, Any]]
    ) -> None:
        """Collect one model message.

        Args:
            text: The message's answer text, which may carry a reasoning trace.
            reasoning: The message's separately reported reasoning trace.
            tool_calls: The calls the model made in this message.
        """
        inline_reasoning, answer = split_think(text)
        self.reasoning += reasoning + inline_reasoning
        self.answer += answer

        for tool_call in tool_calls or []:
            args = tool_call.get("args") or {}
            body = "\n".join(f"{k}: {v}" for k, v in args.items())
            self.reasoning += (
                f"\n\n````\nUsing tool: {tool_call.get('name')}\n{body}\n````\n\n"
            )

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

    def __init__(self, **agent_kwargs: Any):
        """Build a deep agent.

        Args:
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

    def _drive(self, payload: Any, turn: TurnOutput) -> None:
        """Run the graph until it finishes or pauses for a decision.

        Args:
            payload: The graph input, or a resume command.
            turn: Collects what the run produces.
        """
        # Draining the messages is what drives the run forward. A pause ends
        # the drain and is left in place: the checkpointer holds it until a
        # decision arrives on a later turn.
        run = self.agent.stream_events(payload, config=self._config, version="v3")
        for message in run.messages:
            turn.add_message(
                str(message.text), str(message.reasoning), message.tool_calls.get()
            )

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

    def run_single_turn(self, message) -> dict[str, Any]:
        """Run one turn for a single incoming message.

        A message that carries a decision answers the paused run instead of
        starting a new one.

        Args:
            message: An incoming chat message, whose first content part carries
                the user's text.

        Returns:
            The agent's non-empty ``text`` answer, its ``reasoning`` trace, and
            the ``interrupt`` the run is now paused on, if any. A run that failed
            leaves no answer, so the collected error takes its place. A completed
            run without answer text receives a recoverable fallback message.

        Raises:
            StaleDecision: The message answered an interrupt that is not pending.
            InvalidDecision: The decision was malformed or is not allowed.
        """
        text = message["content"][0]["text"]
        decision = self._as_decision(text)
        turn = TurnOutput()

        if decision is not None:
            # Raised before the run is touched, so a refused decision leaves
            # the graph paused exactly as it was.
            payload = self._resume_command(decision)
        else:
            payload = {"messages": [{"role": "user", "content": text}]}

        if not turn.error:
            try:
                self._drive(payload, turn)
            except Exception as exc:
                # Run failures deliberately travel as chat output during local
                # development.
                turn.error = f"The agent run failed: {exc}"

        interrupt = self._pending_interrupt()
        if interrupt is not None:
            turn.answer += "Please decide how you want to proceed:\n"

        return turn.as_answer(
            self._interrupt_view(interrupt) if interrupt is not None else None
        )
