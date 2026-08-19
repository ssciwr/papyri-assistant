"""Provide a connector for deepagents agents driven by LangGraph's v3 event stream."""

import json
import os
import uuid
from pprint import pformat
from typing import Any
from collections.abc import Mapping
from pathlib import Path
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from langchain.agents.middleware import (
    SummarizationMiddleware,
    LLMToolSelectorMiddleware,
)
import yaml
from pprint import pprint

from .base import BaseAgent
from .message_processor import MessageProcessorTerminal
from .utils import utils

# TODO:
# - integrate with mcp -> connection to database
# - integrate subagents into fastAPI


def create_agent_from_config(path: str):
    """TODO

    Args:
        path (str): TODO

    Returns:
        _type_: TODO
    """

    with open(Path(path).resolve(), "r") as f:
        config = yaml.safe_load(f)

    # recurse
    def _process_config(value: Any):
        if isinstance(value, list):
            result = []
            for element in value:
                result.append(_process_config(element))
            return result

        elif isinstance(value, dict):
            result = {}
            for i in value:
                result[i] = _process_config(
                    value[i],
                )  # TODO: recursion is wrong, need one in list as well
            return result
        else:
            return utils.load_type(value)

    cfg = {}
    for k, v in config.items():
        cfg[k] = _process_config(v)

    return LangChainAgent([], kwargs=cfg)


class LangChainAgent(BaseAgent):
    """Connect to a deepagents agent and stream its events."""

    def __init__(
        self,
        options_to_pass: list[str],
        kwargs: dict[str, Any] | None = None,
        message_processor_type: type | None = None,
        message_processor_args: list[Any] | None = None,
        message_processor_kwargs: Mapping[str, Any] | None = None,
    ):
        """Build a deep agent.

        Args:
            options_to_pass: Unused. The interface carries command-line options
                for connectors that drive an agent subprocess; a deep agent is
                built in-process from keyword arguments instead.
            kwargs: Keyword arguments for ``create_deep_agent``, such as
                ``model``, ``tools``, ``system_prompt`` and ``interrupt_on``.
                ``middleware`` and ``permissions`` are given as
                ``{"type": ..., "kwargs": {...}}`` entries and instantiated here.
                A ``checkpointer`` is added when none is supplied, because
                interrupts cannot be resumed without one.
        """
        super().__init__(options_to_pass, kwargs)

        agent_kwargs = dict(kwargs or {})
        agent_kwargs.setdefault(
            "checkpointer", InMemorySaver()
        )  # TODO: make the checkpointer configurable

        model = agent_kwargs.get("model")
        if isinstance(model, Mapping):
            model_kwargs = dict(model.get("kwargs") or {})
            model_kwargs.setdefault("model", os.getenv("LLM_MODEL"))
            model_kwargs.setdefault("base_url", os.getenv("LLM_API_URL"))
            model_kwargs.setdefault("api_key", os.getenv("LLM_API_KEY", "EMPTY"))
            agent_kwargs["model"] = model["type"](**model_kwargs)

        agent_kwargs["middleware"] = [
            self._build_middleware(middleware_def, agent_kwargs.get("model"))
            for middleware_def in agent_kwargs.get("middleware") or []
        ]

        if "permissions" in agent_kwargs:
            agent_kwargs["permissions"] = [
                self._build_permission(permission_def)
                for permission_def in agent_kwargs["permissions"] or []
            ]

        self.agent = create_deep_agent(**agent_kwargs)
        self.thread_id = str(uuid.uuid4())
        self._pending: dict[str, Any] | Command | None = None
        self._run: Any | None = None

        processor_type = (
            utils.load_type(message_processor_type) or MessageProcessorTerminal
        )
        self.message_processor = processor_type(
            *(message_processor_args or []), **(message_processor_kwargs or {})
        )

    @staticmethod
    def _build_middleware(middleware_def: Mapping[str, Any], model: Any) -> Any:
        """Build one middleware from its config entry.

        Args:
            middleware_def: A ``{"type": ..., "kwargs": {...}}`` mapping, where
                the type is a middleware class such as
                ``langchain.agents.middleware.TodoListMiddleware``.
            model: The agent's chat model, handed to the middlewares that run a
                model of their own instead of the agent's.

        Returns:
            The instantiated middleware, ready to hand to ``create_deep_agent``.
        """
        middleware_type = utils.load_type(middleware_def["type"])
        middleware_kwargs = dict(middleware_def.get("kwargs") or {})

        # some middleware needs a model being passed explicitly
        if middleware_type in (SummarizationMiddleware, LLMToolSelectorMiddleware):
            middleware_kwargs.setdefault("model", model)

        return middleware_type(**middleware_kwargs)

    @staticmethod
    def _build_permission(permission_def: Mapping[str, Any]) -> Any:
        """Build one filesystem access rule from its config entry.

        Args:
            permission_def: A ``{"type": ..., "kwargs": {...}}`` mapping, where
                the type is a permission class such as
                ``deepagents.FilesystemPermission``.

        Returns:
            The instantiated rule, ready to hand to ``create_deep_agent``.
        """
        permission_type = utils.load_type(permission_def["type"])
        permission_kwargs = dict(permission_def.get("kwargs") or {})

        # FilesystemPermission insists on absolute paths and rejects "~", so the
        # shell-style shorthands a config is written with are resolved here.
        if "paths" in permission_kwargs:
            permission_kwargs["paths"] = [
                os.path.expanduser(os.path.expandvars(path))
                for path in permission_kwargs["paths"]
            ]

        return permission_type(**permission_kwargs)

    @property
    def _config(
        self,
    ) -> dict[str, Any]:  # TODO: why is this needed, I am not sure this does much
        """Return the runnable config binding a run to the current thread.

        Returns:
            A config carrying the thread id the checkpointer keys state on.
        """
        return {"configurable": {"thread_id": self.thread_id}}

    def _process_input_message(self, user_input: str):
        """Convert user input into an input payload.

        Args:
            user_input: Raw input entered by the user.

        Returns:
            An input payload for the underlying langraph, or ``None`` for an unsupported wrapper
            command.
        """
        command = user_input.strip().split(" ", 1)[0]

        if command.startswith(("\\", "/")):
            return None  # unsupported wrapper command

        return {"messages": [{"role": "user", "content": user_input}]}

    def send_message(self, input: str):
        """Stage user input for the next run.

        The payload is held until ``get_answers`` consumes it, because a v3
        run is driven by the caller's iteration rather than by writing to a
        process.

        Args:
            input: Raw user input to convert into a graph input payload.
        """
        to_send = self._process_input_message(input)

        if to_send is None:
            self.message_processor._process_input_failure(input)
        else:
            self._pending = to_send

    def get_answers(self):
        """Start a run for the staged payload and yield its messages.

        Iterating the yielded streams is what drives the run forward.

        Yields:
            One ``ChatModelStream`` per model call in the run.
        """
        if self._pending is None:
            return

        # This takes care of the interleaving of steering messages
        # TODO: looks weird. not sure this is  necessary
        pending, self._pending = (
            self._pending,
            None,
        )

        # TODO: I am not too happy that this here sends requests. I think this architecture is way too complicated for what I am trying to do
        self._run = self.agent.stream_events(
            pending,
            config=self._config,
            version="v3",  # TODO: is this necessary?
        )

        yield from self._run.messages  # answer buffer

    def _process_events_tool_call(self, tool_call):
        """Print the name and arguments of a requested tool call.

        Args:
            tool_call: A finalized tool call emitted by the model.
        """
        self.message_processor.process_thinking_message(
            f"**Using tool: {tool_call.get('name')}"
        )

        # direct copy from PiConnector, check there.
        for k, v in (tool_call.get("args") or {}).items():
            fk = pformat(k, compact=True)
            fv = pformat(v, compact=True)
            self.message_processor.process_thinking_message(f"  {fk}: {fv}**")

    def _process_interrupt(self):
        """Collect a decision for every action the run paused on.

        Decisions are staged as a resume payload for the next run, in the same
        order as the requested actions.
        """
        request = self._run.interrupts[0].value
        action_requests = request["action_requests"]
        review_configs = request["review_configs"]

        decisions = [
            self._process_action_request(action, config)
            for action, config in zip(action_requests, review_configs)
        ]

        self._pending = Command(
            resume={"decisions": decisions}
        )  # should this be assignment or appending?

    def _process_action_request(self, action, config):
        """Ask the user how to handle one requested action.

        Args:
            action: The action awaiting review, with its name and arguments.
            config: The review policy for the action, listing which decisions
                the agent will accept for it.

        Returns:
            A decision payload for the action.
        """
        allowed = config["allowed_decisions"]

        self.message_processor.process_system_message(
            f"\nThe agent wants to run: {action['name']}"
        )
        if action.get("description"):
            self.message_processor.process_system_message(f"{action['description']}")
        for k, v in (action.get("args") or {}).items():
            self.message_processor.process_system_message(
                f"  {pformat(k)}: {pformat(v)}"
            )

        for index, decision_type in enumerate(allowed, start=1):
            self.message_processor.process_system_message(f"  {index} {decision_type}")

        decision_type = self._ask_decision_type(allowed)

        if decision_type == "approve":
            return {"type": "approve"}

        if decision_type == "edit":
            return {
                "type": "edit",
                "edited_action": {
                    "name": action["name"],
                    "args": self._ask_edited_args(action.get("args") or {}),
                },
            }

        if decision_type == "reject":
            message = self.message_processor.process_user_input(
                "reason (optional) >> "
            ).strip()
            return (
                {"type": "reject", "message": message}
                if message
                else {"type": "reject"}
            )

        message = ""
        while not message:
            message = self.message_processor.process_user_input(
                "response to the agent >> "
            ).strip()
        return {"type": "respond", "message": message}

    def _ask_decision_type(self, allowed: list[str]) -> str:
        """Read a decision from the numbered menu until the choice is valid.

        Args:
            allowed: The decision types the agent accepts for this action.

        Returns:
            The chosen decision type.
        """
        while True:
            choice = self.message_processor.process_user_input("choice >> ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(allowed):
                return allowed[int(choice) - 1]
            self.message_processor.process_error(
                f"Pick a number between 1 and {len(allowed)}"
            )

    def _ask_edited_args(self, args: dict[str, Any]) -> dict[str, Any]:
        """Read replacement arguments as JSON until they parse.

        Args:
            args: The arguments the model requested, shown as a starting point.

        Returns:
            The replacement arguments.
        """
        # what is this about? check docs
        self.message_processor.process_system_message(
            f"current args: {json.dumps(args)}"
        )

        while True:
            raw = self.message_processor.process_user_input("edited args (JSON) >> ")
            try:
                edited = json.loads(raw)
            except json.JSONDecodeError as exc:
                self.message_processor.process_error(f"Not valid JSON: {exc}")
                continue

            if not isinstance(edited, dict):
                self.message_processor.process_error("Args must be a JSON object.")
                continue

            return edited

    def _process_events_message(self, message):
        """Print one model message as it streams in.

        Raw protocol events are iterated rather than the ``text`` and
        ``reasoning`` projections, because both projections only finish at the
        end of the message; draining either one would buffer the whole message
        instead of printing it as it arrives.

        Args:
            message: A ``ChatModelStream`` for a single model call.
        """
        for event in message:
            if event.get("event") != "content-block-delta":
                continue

            delta = event.get("delta") or {}

            if delta.get("type") == "text-delta":
                self.message_processor.process_answer_message(delta.get("text", ""))
            elif delta.get("type") == "reasoning-delta":
                self.message_processor.process_thinking_message(
                    delta.get("reasoning", "")
                )

        for tool_call in message.tool_calls.get() or []:
            self._process_events_tool_call(tool_call)

    def process_events(self):
        """Drive the staged run to completion, pausing for interrupts."""
        # implements the control flow for event processing.
        # delegates implement treatment of events
        while self._pending is not None:
            for message in self.get_answers():
                self._process_events_message(message)

            self.message_processor.reset_output_config()

            if self._run.interrupted:
                self._process_interrupt()

    def answer_with_chat(self, message) -> Any:
        """_summary_

        Args:
            message (_type_): _description_

        Returns:
            Any: _description_
        """
        # TODO. This needs to become the thing fastAPI builds on
        # - eats list of json or text through messageprocessor
        # - makes it pending
        # then let's get_answers do its thing
        # then do all the other stuff

        print("incoming messages")
        pprint(message)
        self.send_message(message["content"][0]["text"])

        # compose message:
        full_answer = []
        full_reasoning = []
        while self._pending is not None:
            for answer in self.get_answers():
                for event in answer:
                    if event.get("event") != "content-block-delta":
                        continue
                    delta = event.get("delta") or {}
                    print("type: ", delta.get("type"))
                    if delta.get("type") == "text-delta":
                        full_answer.append(delta.get("text", ""))
                    elif delta.get("type") == "reasoning-delta":
                        full_reasoning.append(delta.get("reasoning", ""))

        # TODO: understand the meaning of this

        # for tool_call in message.tool_calls.get() or []:
        #     self._process_events_tool_call(tool_call)
        full_answer = "".join(full_answer)
        print("answer: ")
        pprint(full_answer)

        full_reasoning = "".join(full_reasoning)
        print("reasoning: ")
        pprint(full_reasoning)

        # TODO: understand the meaning of this and how it handles tools
        if self._run.interrupted:
            self._process_interrupt()

        return {"text": full_answer}

    def run(
        self,
    ):
        """Run an interactive loop and render the agent's streaming responses."""

        while True:
            try:
                # this part must go into the answer_with_chat function
                # the message_processor must do the formatting and stuff.
                self.message_processor.set_output_config()

                try:
                    message = self.message_processor.process_user_input(">> ")
                finally:
                    self.message_processor.reset_output_config()

                stripped = message.strip()

                # analogues to PiConnector commands
                # perhaps go and put these into individual processors like done in pi
                if stripped == "/quit":
                    break

                if stripped == "/new":
                    self.thread_id = str(uuid.uuid4())
                    self.message_processor.process_system_message("new session started")
                    continue

                self.send_message(message)

                try:
                    self.process_events()
                except Exception as exc:
                    self._pending = None

                    self.message_processor.process_error(f"The agent run failed: {exc}")
            except KeyboardInterrupt:
                try:
                    self.message_processor.process_answer_message("bye!")
                finally:
                    self.message_processor.reset_output_config()

                break

        self.teardown()

    def teardown(self) -> int:
        """Stop a run that was left partially drained.

        Returns:
            Zero. The agent runs in this process, so there is no exit code to
            report.
        """
        if self._run is not None:
            self._run.abort()
            self._run = None

        return 0
