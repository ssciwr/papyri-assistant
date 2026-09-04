"""Provide a connector for deepagents agents driven by LangGraph's v3 event stream."""

import json
import re
import uuid
from collections.abc import Iterator, Mapping
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
_PARTIAL_TAG_LIMIT = 64
_TOKEN_FIELDS = ("input_tokens", "output_tokens", "total_tokens")


class _InlineReasoningParser:
    """Classify inline reasoning without retaining the complete message."""

    def __init__(self, *, assume_prefilled: bool):
        self._mode = "reasoning" if assume_prefilled else "prefix"
        self._buffer = ""

    def feed(self, delta: str) -> list[tuple[str, str]]:
        self._buffer += delta
        return self._drain()

    def finish(self) -> list[tuple[str, str]]:
        if not self._buffer:
            return []
        kind = "reasoning" if self._mode == "reasoning" else "text"
        delta, self._buffer = self._buffer, ""
        return [(kind, delta)]

    def _drain(self) -> list[tuple[str, str]]:
        if self._mode == "text":
            delta, self._buffer = self._buffer, ""
            return [("text", delta)] if delta else []

        if self._mode == "prefix":
            candidate = self._buffer.lstrip()
            if not candidate:
                return []
            if not candidate.startswith("<"):
                self._mode = "text"
                return self._drain()

            tag_end = candidate.find(">")
            if tag_end < 0 and len(candidate) <= _PARTIAL_TAG_LIMIT:
                return []
            if tag_end >= 0 and _THINK_OPEN.fullmatch(candidate[: tag_end + 1]):
                self._mode = "reasoning"
                self._buffer = candidate[tag_end + 1 :]
                return self._drain()

            self._mode = "text"
            return self._drain()

        close_tag = _THINK_CLOSE.search(self._buffer)
        if close_tag is not None:
            reasoning = self._buffer[: close_tag.start()]
            answer = self._buffer[close_tag.end() :]
            self._buffer = ""
            self._mode = "text"
            return [
                (kind, text)
                for kind, text in (("reasoning", reasoning), ("text", answer))
                if text
            ]

        possible_tag = self._buffer.rfind("<")
        if possible_tag < 0:
            reasoning, self._buffer = self._buffer, ""
            return [("reasoning", reasoning)] if reasoning else []

        suffix = self._buffer[possible_tag:]
        if ">" in suffix or len(suffix) > _PARTIAL_TAG_LIMIT:
            reasoning, self._buffer = self._buffer, ""
            return [("reasoning", reasoning)]

        reasoning = self._buffer[:possible_tag]
        self._buffer = suffix
        return [("reasoning", reasoning)] if reasoning else []


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
        self.context_window = self._model_context_window(model)
        agent_kwargs = {
            key: value if key == "model" else utils.build(value, {"model": model})
            for key, value in agent_kwargs.items()
        }
        agent_kwargs["model"] = model

        self.agent = create_deep_agent(**agent_kwargs)
        self._verify_config(agent_kwargs)
        self.thread_id = str(uuid.uuid4())

    @staticmethod
    def _model_context_window(model: Any) -> int | None:
        """Read the configured input limit used by DeepAgents summarization."""
        profile = getattr(model, "profile", None)
        if not isinstance(profile, Mapping):
            return None
        value = profile.get("max_input_tokens")
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            return None
        return value

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

    def _stream_drive(self, payload: Any) -> Iterator[dict[str, Any]]:
        """Drive one graph run and report usage after each model call."""
        run = self.agent.stream_events(payload, config=self._config, version="v3")
        usage: dict[str, int] | None = None
        model_call = 0
        for message in run.messages:
            model_call += 1
            # Whether text introduces a tool call is only known when that call
            # appears, so retain just this message's text until it completes.
            pending_text: list[str] = []
            for kind, delta in self._classified_deltas(message):
                if kind == "text":
                    pending_text.append(delta)
                else:
                    yield {"type": kind, "content": delta}

            tool_calls = message.tool_calls.get() or []
            text_type = "reasoning" if tool_calls else "text"
            for delta in pending_text:
                yield {"type": text_type, "content": delta}

            for tool_call in tool_calls:
                args = tool_call.get("args") or {}
                body = "\n".join(f"{key}: {value}" for key, value in args.items())
                yield {
                    "type": "reasoning",
                    "content": (
                        f"\n\n````\nUsing tool: {tool_call.get('name')}\n"
                        f"{body}\n````\n\n"
                    ),
                }

            message_usage = self._message_usage(message)
            if message_usage is not None:
                if usage is None:
                    usage = {field: 0 for field in _TOKEN_FIELDS}
                for field in _TOKEN_FIELDS:
                    usage[field] += message_usage[field]
                yield {
                    "type": "usage",
                    "usage": dict(usage),
                    "model_usage": {
                        "model_call": model_call,
                        **message_usage,
                        "context_window": getattr(self, "context_window", None),
                    },
                }

    @staticmethod
    def _message_usage(message: Any) -> dict[str, int] | None:
        """Read LangChain's normalized usage from a completed model message."""
        output = getattr(message, "output", None)
        raw_usage = getattr(output, "usage_metadata", None)
        if not isinstance(raw_usage, Mapping):
            return None

        usage: dict[str, int] = {}
        for field in _TOKEN_FIELDS:
            value = raw_usage.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                return None
            usage[field] = value
        return usage

    def _classified_deltas(self, message: Any) -> Iterator[tuple[str, str]]:
        """Classify one model message's text and explicit reasoning deltas."""
        parser = _InlineReasoningParser(
            assume_prefilled=getattr(self, "inline_reasoning", False)
        )
        has_reasoning_projection = False

        for kind, delta in self._message_deltas(message):
            if kind == "reasoning":
                if not has_reasoning_projection:
                    has_reasoning_projection = True
                    yield from parser.finish()
                yield kind, delta
            elif has_reasoning_projection:
                yield kind, delta
            else:
                yield from parser.feed(delta)

        if not has_reasoning_projection:
            yield from parser.finish()

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
        """Stream one turn as text and reasoning deltas.

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
        has_answer = False
        failed = False
        usage = None
        model_usage = None

        try:
            for event in self._stream_drive(payload):
                if event["type"] == "usage":
                    usage = event["usage"]
                    model_usage = event["model_usage"]
                if event["type"] == "text" and event["content"].strip():
                    has_answer = True
                yield event
        except Exception as exc:
            failed = True
            yield {"type": "replace", "content": f"The agent run failed: {exc}"}

        interrupt = self._pending_interrupt()
        interrupt_view = None
        if interrupt is not None:
            interrupt_view = self._interrupt_view(interrupt)
            if not failed:
                yield {
                    "type": "text",
                    "content": "Please decide how you want to proceed:\n",
                }
        elif not has_answer and not failed:
            yield {"type": "text", "content": _EMPTY_ANSWER_MESSAGE}

        done: dict[str, Any] = {"type": "done", "interrupt": interrupt_view}
        if usage is not None:
            done["usage"] = usage
            done["model_usage"] = model_usage
        yield done
