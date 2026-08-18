"""Provide a connector for deepagents agents driven by LangGraph's v3 event stream."""

import json
import uuid
from pprint import pformat
from typing import Any

from deepagents import create_deep_agent
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from .base import BaseAgent

USER_COLOR = "\033[36m"  # cyan
ASSISTANT_COLOR = "\x1b[35m"  # magenta
SYSTEM_COLOR = "\033[33m"  # amber
RESET = "\033[0m"
THINKING_STYLE = "\033[3;32m"  # italic green
ERROR_COLOR = "\033[41m"

# TODO:
# - replace the terminal rendering with a MessageProcessor, shared with Pi,
#   so both connectors can serve FastAPI endpoints
# - build create_langchain_agent_from_config once load_type can resolve
#   tools and other Python objects from YAML strings
# - integrate with mcp -> connection to database
# - integrate subagents


class LangChainAgent(BaseAgent):
    """Connect to a deepagents agent and stream its events."""

    def __init__(
        self,
        options_to_pass: list[str],
        kwargs: dict[str, Any] | None = None,
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
        agent_kwargs.setdefault("checkpointer", InMemorySaver())
        self.agent = create_deep_agent(**agent_kwargs)

        self.thread_id = str(uuid.uuid4())
        self._pending: dict[str, Any] | Command | None = None
        self._run: Any | None = None

    @property
    def _config(self) -> dict[str, Any]:
        """Return the runnable config binding a run to the current thread.

        Returns:
            A config carrying the thread id the checkpointer keys state on.
        """
        return {"configurable": {"thread_id": self.thread_id}}

    def _process_input_message(self, user_input: str):
        """Convert user input into a graph input payload.

        Args:
            user_input: Raw input entered by the user.

        Returns:
            A graph input payload, or ``None`` for an unsupported wrapper
            command.
        """
        command = user_input.strip().split(" ", 1)[0]

        if command.startswith(("\\", "/")):
            return None  # unsupported wrapper command

        return {"messages": [{"role": "user", "content": user_input}]}

    def _process_input_failure(self, input: str):
        """Print an error for unsupported user input.

        Args:
            input: Unsupported user input.
        """
        print(
            f"{ERROR_COLOR}{input} is not a known command.{RESET}",
            flush=True,
        )

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
            self._process_input_failure(input)
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

        pending, self._pending = self._pending, None
        self._run = self.agent.stream_events(
            pending,
            config=self._config,
            version="v3",
        )

        yield from self._run.messages

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
                print(
                    f"{ASSISTANT_COLOR}{delta.get('text', '')}{RESET}",
                    end="",
                    flush=True,
                )
            elif delta.get("type") == "reasoning-delta":
                print(
                    f"{THINKING_STYLE}{delta.get('reasoning', '')}{RESET}",
                    end="",
                    flush=True,
                )

        for tool_call in message.tool_calls.get() or []:
            self._process_events_tool_call(tool_call)

    def _process_events_tool_call(self, tool_call):
        """Print the name and arguments of a requested tool call.

        Args:
            tool_call: A finalized tool call emitted by the model.
        """
        print(
            f"\n{THINKING_STYLE}**Using tool: {tool_call.get('name')}**{RESET}",
            flush=True,
        )
        for k, v in (tool_call.get("args") or {}).items():
            fk = pformat(k, compact=True)
            fv = pformat(v, compact=True)
            print(
                f"{THINKING_STYLE}  {fk}: {fv}**{RESET}",
                flush=True,
            )

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

        self._pending = Command(resume={"decisions": decisions})

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

        print(f"\n{SYSTEM_COLOR}The agent wants to run: {action['name']}{RESET}")
        if action.get("description"):
            print(f"{SYSTEM_COLOR}{action['description']}{RESET}")
        for k, v in (action.get("args") or {}).items():
            print(f"{SYSTEM_COLOR}  {pformat(k)}: {pformat(v)}{RESET}")

        for index, decision_type in enumerate(allowed, start=1):
            print(f"{SYSTEM_COLOR}  {index}) {decision_type}{RESET}")

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
            message = input(f"{USER_COLOR}reason (optional) >> {RESET}").strip()
            return {"type": "reject", "message": message} if message else {"type": "reject"}

        message = ""
        while not message:
            message = input(f"{USER_COLOR}response to the agent >> {RESET}").strip()
        return {"type": "respond", "message": message}

    def _ask_decision_type(self, allowed: list[str]) -> str:
        """Read a decision from the numbered menu until the choice is valid.

        Args:
            allowed: The decision types the agent accepts for this action.

        Returns:
            The chosen decision type.
        """
        while True:
            choice = input(f"{USER_COLOR}choice >> {RESET}").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(allowed):
                return allowed[int(choice) - 1]
            print(f"{ERROR_COLOR}Pick a number between 1 and {len(allowed)}.{RESET}")

    def _ask_edited_args(self, args: dict[str, Any]) -> dict[str, Any]:
        """Read replacement arguments as JSON until they parse.

        Args:
            args: The arguments the model requested, shown as a starting point.

        Returns:
            The replacement arguments.
        """
        print(f"{SYSTEM_COLOR}current args: {json.dumps(args)}{RESET}")

        while True:
            raw = input(f"{USER_COLOR}edited args (JSON) >> {RESET}").strip()
            try:
                edited = json.loads(raw)
            except json.JSONDecodeError as exc:
                print(f"{ERROR_COLOR}Not valid JSON: {exc}{RESET}")
                continue

            if not isinstance(edited, dict):
                print(f"{ERROR_COLOR}Args must be a JSON object.{RESET}")
                continue

            return edited

    def process_events(self):
        """Drive the staged run to completion, pausing for interrupts."""
        # implements the control flow for event processing.
        # delegates implement treatment of events
        while self._pending is not None:
            for message in self.get_answers():
                self._process_events_message(message)

            print(f"\n{RESET}", end="", flush=True)

            if self._run.interrupted:
                self._process_interrupt()

    def chat(
        self,
    ):
        """Run an interactive loop and render the agent's streaming responses."""

        while True:
            try:
                print(USER_COLOR, end="", flush=True)
                try:
                    message = input(">> ")
                finally:
                    print(RESET, end="\n", flush=True)

                stripped = message.strip()

                if stripped == "/quit":
                    break

                if stripped == "/new":
                    self.thread_id = str(uuid.uuid4())
                    print(f"{SYSTEM_COLOR}new session started{RESET}", flush=True)
                    continue

                self.send_message(message)

                try:
                    self.process_events()
                except Exception as exc:
                    self._pending = None
                    print(f"{ERROR_COLOR}The agent run failed: {exc}{RESET}", flush=True)
            except KeyboardInterrupt:
                try:
                    print(f"{ASSISTANT_COLOR}bye!")
                finally:
                    print(RESET, end="", flush=True)
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
                api_key=os.environ["LLM_API_KEY"],
                base_url=os.getenv("LLM_API_URL") or None,
            ),
            "system_prompt": "You are a concise, helpful assistant",
            "interrupt_on": {"write_file": True},
        },
    )

    langchain_agent.chat()
