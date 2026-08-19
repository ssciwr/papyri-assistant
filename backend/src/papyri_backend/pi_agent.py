"""Provide connectors and message processors for Pi's JSON-RPC interface."""

import subprocess
import json
from typing import Any, Literal
from collections.abc import Mapping, Sequence
import warnings
import yaml
from pprint import pformat
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from .base import BaseAgent

USER_COLOR = "\033[36m"  # cyan
ASSISTANT_COLOR = "\x1b[35m"  # magenta
SYSTEM_COLOR = "\033[33m"  # amber
RESET = "\033[0m"
THINKING_STYLE = "\033[3;32m"  # italic green
ERROR_COLOR = "\033[41m"

PI_AGENT = None  # agent instance

# TODO:
# - integrate extension management
# - integrate with session manager
# - integrate with mcp -> connection to database
# - integrate with langchain agents


class PiConnector(BaseAgent):
    """Connect to a Pi agent running in RPC mode."""

    def __init__(
        self,
        options_to_pass: list[str],
        subprocess_kwargs: dict[str, Any] | None = None,
        message_processor: type[PiMessageProcessorBase] = PiMessageProcessorTerminal,
    ):
        """Start a Pi RPC subprocess.

        Args:
            options_to_pass: Command-line options passed to the ``pi`` command.
            subprocess_kwargs: Optional keyword arguments for ``subprocess.Popen``.
            message_processor: Processor class used to handle Pi events.
        """
        super().__init__(options_to_pass, subprocess_kwargs)

        self.proc = subprocess.Popen(
            [
                "pi",
            ]
            + options_to_pass,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            **(subprocess_kwargs or {}),
        )
        self.ids: list[str] = []
        self.current_id = 0

        self.input_processors = {
            "/thinking": self._process_command_thinking,
            "/model": self._process_command_model,  # /model model-name
            "/new": self._process_command_new_session,
            "/quit": self._process_command_quit,
            "/history": self._process_command_history,
            "/models": self._process_command_models,
            "/state": self._process_command_state,
            "/steer": self._process_command_steer,
            "/followup": self._process_command_followup,
            "/follow_up": self._process_command_followup,
            "/commands": self._process_get_commands,
            "/abort": self._process_command_abort,  # TODO: doesn't yet work
        }

        self.response_processors = {
            "new_session": self._process_response_new,
            "get_state": self._process_response_state,
            "get_messages": self._process_response_history,
            "get_available_models": self._process_response_models,
            "set_thinking_level": self._process_response_thinking,
            "set_model": self._process_response_model,
            "get_commands": self._process_response_commands,
        }

        self.message_processor = message_processor()  # no arguments

        # ask for model list once and save it, so we can look them up easily later
        self.proc.stdin.write(
            json.dumps(
                {
                    "type": "get_available_models",
                }
            )
            + "\n"
        )
        self.proc.stdin.flush()

        self.models = {}
        for event in self.get_answers():
            if event.get("type") == "response" and event.get("success"):
                if event.get("command") == "prompt":
                    continue
                else:
                    result = self.response_processors[event.get("command")](
                        event.get("data")
                    )
                    for r in result:
                        r = yaml.safe_load(r)
                        self.models[r["name"]] = {
                            "id": r["id"],
                            "provider": r["provider"],
                        }
                    break
        self._event_thread: threading.Thread | None = None
        self.streaming_behavior = "steer"

    def _process_get_commands(self, message: list[str]):
        """Build a request for the commands available from Pi.

        Args:
            message: Parsed command input. The value is unused.

        Returns:
            A ``get_commands`` request payload.
        """
        processed = {"type": "get_commands"}
        return processed

    def _process_command_steer(self, messages: list[str]):
        """Build a request to steer the active agent run.

        Args:
            messages: Parsed command and steering instruction.

        Returns:
            A ``steer`` request payload.
        """
        processed = {"type": "steer", "message": " ".join(messages)}
        return processed

    def _process_command_followup(self, messages: list[str]):
        """Build a follow-up request for the active agent run.

        Args:
            messages: Parsed command and follow-up instruction.

        Returns:
            A ``follow_up`` request payload.
        """
        processed = {"type": "follow_up", "message": " ".join(messages)}
        return processed

    def _process_command_thinking(self, messages: list[str]):
        """Build a request to change the model's thinking level.

        Args:
            messages: Parsed command followed by the requested level.

        Returns:
            A ``set_thinking_level`` request payload.
        """
        processed = {"type": "set_thinking_level", "level": messages[1]}
        return processed

    def _process_command_abort(self, messages: list[str]):
        """Build a request to abort the active agent run.

        Args:
            messages: Parsed command input. The value is unused.

        Returns:
            An ``abort`` request payload.
        """
        return {"type": "abort"}

    def _process_command_models(self, messages: list[str]):
        """Build a request for the models available to Pi.

        Args:
            messages: Parsed command input. The value is unused.

        Returns:
            A ``get_available_models`` request payload.
        """
        return {
            "type": "get_available_models",
        }

    def _process_command_model(self, messages: list[str]):
        """Build a request to select a model by name.

        Args:
            messages: Parsed command followed by the requested model name.

        Returns:
            A model-selection request or a prompt describing invalid input.
        """
        if len(messages) < 2:
            message = {
                "type": "prompt",
                "message": f"Tell the user that they have to provide a model name for requesting a different model. You have {self.models} available",
            }

        model_name = messages[1]
        model_data = self.models.get(model_name)
        if not model_data:
            message = {
                "type": "prompt",
                "message": f"Tell the user that they requested a non-existent model. You have {self.models} available",
            }
        else:
            message = {
                "type": "set_model",
                "provider": model_data["provider"],
                "modelId": model_data["id"],
            }

        return message

    def _process_command_new_session(self, messages: list[str]):
        """Build a request to start a new Pi session.

        Args:
            messages: Parsed command input. The value is unused.

        Returns:
            A ``new_session`` request payload.
        """
        return {
            "type": "new_session",
        }

    def _process_command_quit(self, messages: list[str]):
        """Return the parsed quit command unchanged.

        Args:
            messages: Parsed quit command.

        Returns:
            The unchanged parsed command.
        """
        return messages

    def _process_command_history(self, messages: list[str]):
        """Build a request for the current session's message history.

        Args:
            messages: Parsed command input. The value is unused.

        Returns:
            A ``get_messages`` request payload.
        """
        return {
            "type": "get_messages",
        }

    def _process_command_state(self, messages: list[str]):
        """Build a request for the current Pi session state.

        Args:
            messages: Parsed command input. The value is unused.

        Returns:
            A ``get_state`` request payload.
        """
        return {
            "type": "get_state",
        }

    def _process_response_commands(self, message):
        """Format the commands available from Pi.

        Args:
            message: Response payload containing command metadata.

        Returns:
            Command names and descriptions separated by blank lines.
        """
        commands = message.get("commands", [])
        if not commands:
            return "No commands available."

        return "\n\n".join(
            f"{command.get('name', '')}: {command.get('description', '')}"
            for command in commands
        )

    def _process_response_new(self, message):
        """Format a new-session command response.

        Args:
            message: Response payload returned by Pi.

        Returns:
            A one-item list describing whether session creation succeeded.
        """
        if message["cancelled"]:
            return ["new session cancelled"]
        return ["new session started"]

    def _process_response_state(self, message):
        """Format the current Pi session state as YAML.

        Args:
            message: State payload returned by Pi.

        Returns:
            A one-item list containing formatted YAML.
        """
        formatted = yaml.safe_dump(
            message,
            sort_keys=False,
            default_flow_style=False,
            width=120,
        ).rstrip()
        return [formatted]

    def _process_response_history(self, message: dict[str, Any]):
        """Format text messages from the current session history.

        Args:
            message: History payload returned by Pi.

        Returns:
            Formatted text entries, colorized by message role.
        """
        processed_list = []
        for history_message in message["messages"]:
            contentlist = history_message["content"]
            for content in contentlist:
                if content["type"] == "text":
                    color = USER_COLOR
                    if history_message["role"] == "assistant":
                        color = ASSISTANT_COLOR
                    formatted = f">> {color}{content['text']}"
                    processed_list.append(formatted)
        return processed_list

    def _process_response_models(self, message):
        """Format the available Pi models as YAML.

        Args:
            message: Models payload returned by Pi.

        Returns:
            A formatted YAML entry for each available model.
        """
        processed_list = []

        for model in message["models"]:
            formatted = yaml.safe_dump(
                model,
                sort_keys=False,
                default_flow_style=False,
                width=120,
            ).rstrip()
            processed_list.append(formatted)
        return processed_list

    def _process_response_thinking(self, message):
        """Format a thinking-level command response.

        Args:
            message: Response payload returned by Pi.

        Returns:
            A confirmation message for the configured thinking level.
        """

        return "Model's thinking level has been changed"

    def _process_response_model(self, message):
        """Format a model-selection response.

        Args:
            message: Response payload containing the selected model name.

        Returns:
            A confirmation naming the selected model.
        """
        return f"Model has been switched to {message['name']}"

    def _process_input_message(self, user_input: str):
        """Convert user input into a Pi RPC request payload.

        Args:
            user_input: Raw input entered by the user.

        Returns:
            The matching command payload, a prompt payload, or ``None`` for an
            unsupported wrapper command.
        """
        parts = user_input.strip().split(" ", 1)
        command = parts[
            0
        ]  # split input to get command and arguments. Remerge when it's a prompt

        if command in self.input_processors:
            return self.input_processors[command](parts)

        elif command.startswith(("\\", "/")):
            return None  # unsupported wrapper command

        return {
            "id": self.current_id,
            "type": "prompt",
            "message": user_input,
            "streamingBehavior": self.streaming_behavior,
        }

    def send_message(self, input: str):
        """send_message a serialized RPC request to the Pi process.

        Args:
            input: Raw user input to convert into a request.
        """
        self.current_id += 1

        to_send = self._process_input_message(input)
        if not to_send:
            self.message_processor._process_input_failure(input)
        else:
            self.proc.stdin.write(json.dumps(to_send) + "\n")
            self.proc.stdin.flush()

    def get_answers(self):
        """Yield decoded RPC events from the Pi process standard output.

        Yields:
            Decoded JSON event payloads emitted by Pi.
        """
        for line in self.proc.stdout:
            yield json.loads(line)

    def process_events(self):
        """Read and dispatch Pi events until the current request settles."""
        # implements the control flow for event processing.
        # delegates implement treatment of events
        for event in self.get_answers():
            if event.get("type") == "extension_ui_response":
                self.message_processor._process_events_extension_ui_response(event)
            elif event.get("type") == "response":
                if event.get("success"):
                    if event.get("command") == "prompt":
                        continue
                    else:
                        result = self.response_processors[event.get("command")](
                            event.get("data")
                        )
                        self.message_processor._process_events_command_response(result)
                        break  # no further messages after the response to a command
                else:
                    print(
                        f"{SYSTEM_COLOR}Error, command {event.get('command')} failed{RESET}"
                    )

            elif event.get("type") == "message_update":
                assistant_message_event = event.get("assistantMessageEvent", {})
                self.message_processor._process_events_message_update(
                    assistant_message_event
                )
            elif event.get("type") == "tool_execution_start":
                self.message_processor._process_events_tool_usage_start(event)
            elif event.get("type") == "tool_execution_end":
                self.message_processor._process_events_tool_usage_end(event)

            elif event.get("type") == "agent_settled":
                print(f"\n{RESET}{USER_COLOR}")
                break
            else:
                pass  # ignore all others

    def run(
        self,
    ):
        """Run an interactive loop and render Pi's streaming responses."""

        while True:
            try:
                message = "nothing"
                print(USER_COLOR, end="", flush=True)
                try:
                    message = input(">> ")
                    if message.strip() == "/quit":
                        break
                finally:
                    print(RESET, end="\n", flush=True)
                self.send_message(message)

                if self._event_thread is None or not self._event_thread.is_alive():
                    self._event_thread = threading.Thread(
                        target=self.process_events,
                        daemon=True,
                    )
                    self._event_thread.start()
            except KeyboardInterrupt:
                try:
                    print(f"{ASSISTANT_COLOR}bye!")
                finally:
                    print(RESET, end="", flush=True)
                break

        self.teardown()

    def teardown(self) -> int:
        """Terminate Pi and wait for it to exit.

        Returns:
            Pi's exit code. The process is killed if it does not stop within
            five seconds.
        """
        self.proc.terminate()

        try:
            exit_code = self.proc.wait(timeout=5)

            if exit_code not in [0, 143]:
                warnings.warn(
                    f"Warning, Pi Agent subprocess exited with abnormal exit code {exit_code}"
                )

        except subprocess.TimeoutExpired:
            self.proc.kill()
            exit_code = self.proc.wait()

        if self._event_thread:
            self._event_thread.join()

        return exit_code


def create_pi_agent(pi_agent_args: list[str], kwargs: dict[str, Any]) -> PiConnector:
    global PI_AGENT
    if PI_AGENT is None:
        args = list(
            set(["--mode", "rpc"] + pi_agent_args)
        )  # remove duplicates in case rpc is given already for instance.
        PI_AGENT = PiConnector(
            options_to_pass=args,
            subprocess_kwargs=kwargs,
            message_processor=PiMessageProcessorAPI,
        )
    return PI_AGENT


def create_pi_agent_from_config(config_path: str) -> PiConnector:
    with open(Path(config_path).resolve()) as f:
        cfg = yaml.safe_load(f)

    pi_agent_args = cfg["agent_options"]
    subprocess_kwargs = cfg["subprocess_kwargs"]

    return create_pi_agent(pi_agent_args, subprocess_kwargs)


if __name__ == "__main__":
    pi_agent = PiConnector(
        [
            "--mode",
            "rpc",
            "--no-session",
            # "--no-skills",
            "--no-prompt-templates",
            "--no-context-files",
            "--tools",
            "read, web_search, write",
            # "pi-subagents",
            # "--extension",
            # "--tools read,web-search",
        ],
    )

    pi_agent.chat()
