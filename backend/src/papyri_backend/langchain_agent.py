"""Provide a connector for deepagents agents driven by LangGraph's v3 event stream."""

import json
import uuid
from pprint import pformat
from typing import Any
from collections.abc import Mapping

from deepagents import create_deep_agent
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from .base import BaseAgent
from .utils import utils


# USER_COLOR = "\033[36m"  # cyan
# ASSISTANT_COLOR = "\x1b[35m"  # magenta
# SYSTEM_COLOR = "\033[33m"  # amber
# RESET = "\033[0m"
# THINKING_STYLE = "\033[3;32m"  # italic green
# ERROR_COLOR = "\033[41m"


# TODO:
# - integrate with mcp -> connection to database
# - integrate subagents


class LangChainAgent(BaseAgent):
    """Connect to a deepagents agent and stream its events."""

    def __init__(
        self,
        options_to_pass: list[str],
        kwargs: dict[str, Any] | None = None,
        message_processor_type: str | None = None,
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
                A ``checkpointer`` is added when none is supplied, because
                interrupts cannot be resumed without one.
        """
        super().__init__(options_to_pass, kwargs)

        agent_kwargs = dict(kwargs or {})
        agent_kwargs.setdefault(
            "checkpointer", InMemorySaver()
        )  # TODO: make the checkpointer configurable

        agent_kwargs["model"]["kwargs"].setdefault("model", os.getenv("LLM_MODEL"))
        agent_kwargs["model"]["kwargs"].setdefault("base_url", os.getenv("LLM_API_URL"))
        agent_kwargs["model"]["kwargs"].setdefault(
            "api_key", os.getenv("LLM_API_KEY", "EMPTY")
        )

        self.agent = create_deep_agent(**agent_kwargs)

        self.thread_id = str(uuid.uuid4())
        self._pending: dict[str, Any] | Command | None = None
        self._run: Any | None = None

        self.message_processor = utils.load_type(message_processor_type)(
            *(message_processor_args or []), **(message_processor_kwargs or {})
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

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "LangChainAgent":
        """Build a new agent from config dictionary containing all needed kwargs.

        Args:
            config (dict[str, Any]): Needed kwargs. May contain python types/entities as dotted path strings
            pointing to modules, e.g. "moduleA.moduleB.class". This will be resolved to moduleA.moduleB.class
            and imported via importlib

        Returns:
            LangChainAgent: Newly created LangChainAgent instance, built from the supplied kwargs
        """

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

        return cls([], kwargs=cfg)

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
        pending, self._pending = (
            self._pending,
            None,
        )  # what the hell is that? this is looks like a big Anti-pattern? self._pending = "pending input"
        self._run = self.agent.stream_events(
            pending,
            config=self._config,
            version="v3",
        )

        yield from self._run.messages  # answer buffer

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
                # print(
                #     f"{ASSISTANT_COLOR}{delta.get('text', '')}{RESET}",
                #     end="",
                #     flush=True,
                # )
                self.message_processor.process_answer_message(delta.get("text", ""))
            elif delta.get("type") == "reasoning-delta":
                # print(
                #     f"{THINKING_STYLE}{delta.get('reasoning', '')}{RESET}",
                #     end="",
                #     flush=True,
                # )
                self.message_processor.process_thinking_message(
                    delta.get("reasoning", "")
                )

        for tool_call in message.tool_calls.get() or []:
            self._process_events_tool_call(tool_call)

    def _process_events_tool_call(self, tool_call):
        """Print the name and arguments of a requested tool call.

        Args:
            tool_call: A finalized tool call emitted by the model.
        """
        # print(
        #     f"\n{THINKING_STYLE}**Using tool: {tool_call.get('name')}**{RESET}",
        #     flush=True,
        # )
        self.message_processor.process_thinking_message(
            f"**Using tool: {tool_call.get('name')}"
        )

        # direct copy from PiConnector, check there.
        for k, v in (tool_call.get("args") or {}).items():
            fk = pformat(k, compact=True)
            fv = pformat(v, compact=True)
            # print(
            #     f"{THINKING_STYLE}  {fk}: {fv}**{RESET}",
            #     flush=True,
            # )
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

        # print(f"\n{SYSTEM_COLOR}The agent wants to run: {action['name']}{RESET}")
        self.message_processor.process_system_message(
            f"\nThe agent wants to run: {action['name']}"
        )
        if action.get("description"):
            # print(f"{SYSTEM_COLOR}{action['description']}{RESET}")
            self.message_processor.process_system_message(f"{action['description']}")
        for k, v in (action.get("args") or {}).items():
            # print(f"{SYSTEM_COLOR}  {pformat(k)}: {pformat(v)}{RESET}")
            self.message_processor.process_system_message(
                f"  {pformat(k)}: {pformat(v)}"
            )

        for index, decision_type in enumerate(allowed, start=1):
            # print(f"{SYSTEM_COLOR}  {index} {decision_type}{RESET}")
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
            # message = input(f"{USER_COLOR}reason (optional) >> {RESET}").strip()
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
            # message = input(f"{USER_COLOR}response to the agent >> {RESET}").strip()
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
            # choice = input(f"{USER_COLOR}choice >> {RESET}").strip()
            choice = self.message_processor.process_user_input("choice >> ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(allowed):
                return allowed[int(choice) - 1]
            # print(f"{ERROR_COLOR}Pick a number between 1 and {len(allowed)}.{RESET}")
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
        # print(f"{SYSTEM_COLOR}current args: {json.dumps(args)}{RESET}")
        self.message_processor.process_system_message(
            f"current args: {json.dumps(args)}"
        )

        while True:
            # raw = input(f"{USER_COLOR}edited args (JSON) >> {RESET}").strip()
            raw = self.message_processor.process_user_input("edited args (JSON) >> ")
            try:
                edited = json.loads(raw)
            except json.JSONDecodeError as exc:
                # print(f"{ERROR_COLOR}Not valid JSON: {exc}{RESET}")
                self.message_processor.process_error(f"Not valid JSON: {exc}")
                continue

            if not isinstance(edited, dict):
                # print(f"{ERROR_COLOR}Args must be a JSON object.{RESET}")
                self.message_processor.process_error("Args must be a JSON object.")
                continue

            return edited

    def process_events(self):
        """Drive the staged run to completion, pausing for interrupts."""
        # implements the control flow for event processing.
        # delegates implement treatment of events
        while self._pending is not None:
            for message in self.get_answers():
                self._process_events_message(message)

            # print(f"\n{RESET}", end="", flush=True)
            self.message_processor.reset_output_config()

            if self._run.interrupted:
                self._process_interrupt()

    def chat(
        self,
    ):
        """Run an interactive loop and render the agent's streaming responses."""

        while True:
            try:
                # print(USER_COLOR, end="", flush=True)
                self.message_processor.set_output_config()

                try:
                    # message = input(">> ")
                    message = self.message_processor.process_user_input(">> ")
                finally:
                    # print(RESET, end="\n", flush=True)
                    self.message_processor.reset_output_config()

                stripped = message.strip()

                # analogues to PiConnector commands
                # perhaps go and put these into individual processors like done in pi
                if stripped == "/quit":
                    break

                if stripped == "/new":
                    self.thread_id = str(uuid.uuid4())
                    # print(f"{SYSTEM_COLOR}new session started{RESET}", flush=True)
                    self.message_processor.process_system_message("new session started")
                    continue

                self.send_message(message)

                try:
                    self.process_events()
                except Exception as exc:
                    self._pending = None
                    # print(
                    #     f"{ERROR_COLOR}The agent run failed: {exc}{RESET}", flush=True
                    # )
                    self.message_processor.process_error(f"The agent run failed: {exc}")
            except KeyboardInterrupt:
                try:
                    # print(f"{ASSISTANT_COLOR}bye!")
                    self.message_processor.process_answer_message("bye!")
                finally:
                    # print(RESET, end="", flush=True)
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


if __name__ == "__main__":
    import os
    from langchain_openai import ChatOpenAI

    from .settings import load_environment

    # Experimental entry point for trying the connector out by hand. Reads the
    # same LLM_* variables as the rest of the backend, so it talks to whichever
    # OpenAI-compatible endpoint .env points at.
    load_environment()

    langchain_agent = LangChainAgent(
        [],
        {
            "model": ChatOpenAI(
                model=os.environ["LLM_MODEL"],
                api_key=os.environ.get("LLM_API_KEY", "EMPTY"),
                base_url=os.getenv("LLM_API_URL"),
            ),
            "system_prompt": "You are a concise, helpful assistant",
            "interrupt_on": {"write_file": True},
        },
    )

    langchain_agent.chat()
