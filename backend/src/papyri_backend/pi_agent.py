import subprocess
import json
from typing import Any, Literal
from collections.abc import Mapping, Sequence
import warnings
import yaml
from dataclasses import dataclass
from pprint import pformat

USER_COLOR = "\033[36m"  # cyan
ASSISTANT_COLOR = "\x1b[35m"  # magenta
SYSTEM_COLOR = "\033[33m"  # amber
RESET = "\033[0m"


class AgentConnectorBase:
    """Define the interface for connectors that communicate with AI agents."""

    def __init__(
        self,
        options_to_pass: list[str],
        subprocess_kwargs: dict[str, Any] | None = None,
    ):
        """Initialize a connector with agent command-line options.

        Args:
            options_to_pass: Command-line options passed to the agent process.
            subprocess_kwargs: Optional keyword arguments for creating the process.
        """
        ...

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "AgentConnectorBase":
        """Create a connector from its configuration mapping.

        Args:
            config: Connector configuration values.

        Returns:
            A configured connector instance.
        """
        ...

    def chat(self, raw_message: str):
        """Send a message to the agent and display its response.

        Args:
            raw_message: The user message to send.
        """
        ...

    def teardown(self) -> int:
        """Stop the underlying agent process.

        Returns:
            The process exit code.
        """
        ...


class PiConnector(AgentConnectorBase):
    """Connect to a Pi agent running in RPC mode."""

    def __init__(
        self,
        options_to_pass: list[str],
        subprocess_kwargs: dict[str, Any] | None = None,
    ):
        """Start a Pi RPC subprocess.

        Args:
            options_to_pass: Command-line options passed to the ``pi`` command.
            subprocess_kwargs: Optional keyword arguments for ``subprocess.Popen``.
        """
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

        self.commands = {
            "/new": {
                "message": {
                    "type": "new_session",
                },
            },
            "/state": {
                "message": {
                    "type": "get_state",
                },
            },
            "/history": {
                "message": {
                    "type": "get_messages",
                },
            },
            "/models": {
                "message": {
                    "type": "get_available_models",
                },
            },
            "/thinking": {
                "message": {"type": "set_thinking_level", "level": "medium"},
            },
        }

        self.response_processors = {
            "new_session": self._process_new,
            "get_state": self._process_state,
            "get_messages": self._process_history,
            "get_available_models": self._process_models,
            "set_thinking_level": self._process_thinking,
        }

        super().__init__(options_to_pass, subprocess_kwargs)

    def _process_new(self, message):
        """Format a new-session command response.

        Args:
            message: Response payload returned by Pi.

        Returns:
            A one-item list describing whether session creation succeeded.
        """
        if message["cancelled"]:
            return ["new session cancelled"]
        return ["new session started"]

    def _process_state(self, message):
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

    def _process_history(self, message: dict[str, Any]):
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

    def _process_models(self, message):
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

    def _process_thinking(self, message):
        """Format a thinking-level command response.

        Args:
            message: Response payload returned by Pi.

        Returns:
            A confirmation message for the configured thinking level.
        """
        # A successful set_thinking_level response has no data payload.
        return ["thinking level set to medium"]

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "PiConnector":
        """Create a Pi connector from configuration values.

        Args:
            config: Mapping containing ``pi_options`` and optional
                ``subprocess_kwargs`` values.

        Returns:
            A configured Pi connector.
        """
        options = config["pi_options"]
        subprocess_kwargs = config.get(
            "subprocess_kwargs",
            {
                "stdin": subprocess.PIPE,
                "stdout": subprocess.PIPE,
                "text": True,
            },
        )

        return cls(options, subprocess_kwargs)

    def _process_input_message(self, input: str):
        """Convert user input into a Pi RPC request payload.

        Args:
            input: Raw input entered by the user.

        Returns:
            The matching command payload or a prompt payload.
        """
        normalized = input.lower().strip()
        if normalized in self.commands:
            raw_command = self.commands[normalized]["message"]

            split_command = normalized.split(" ")
            if len(split_command) > 1:
                print(split_command)

            return raw_command
        else:
            return {"id": self.current_id, "type": "prompt", "message": input}

    def _send(self, input: str, type: str = "prompt"):
        """Send a serialized RPC request to the Pi process.

        Args:
            input: Raw user input to convert into a request.
            type: Requested RPC message type. Currently unused.
        """
        self.current_id += 1
        to_send = self._process_input_message(input)
        self.proc.stdin.write(json.dumps(to_send) + "\n")
        self.proc.stdin.flush()

    def _read_events(self):
        """Yield decoded RPC events from the Pi process standard output.

        Yields:
            Decoded JSON event payloads emitted by Pi.
        """
        for line in self.proc.stdout:
            yield json.loads(line)

    def chat(self, raw_message: str):
        """Send a message and render Pi's streaming response to standard output.

        Args:
            raw_message: The message to send to Pi.
        """
        self._send(
            raw_message, type="prompt"
        )  # TODO: this needs auto-detect for different types

        for event in self._read_events():
            if event.get("type") == "response":
                if event.get("success"):
                    if event.get("command") == "prompt":
                        continue
                    else:
                        result = self.response_processors[event.get("command")](
                            event.get("data")
                        )

                        if isinstance(result, Sequence):
                            for res in result:
                                print(f"{SYSTEM_COLOR}{res}", flush=True)
                                print("\n")
                        else:
                            print(f"{SYSTEM_COLOR}{result}")
                        break  # no further messages after the response to a command
                else:
                    print(f"{SYSTEM_COLOR}Error, command {event.get('command')} failed")

            if event.get("type") == "message_update":
                delta = event.get("assistantMessageEvent", {})
                if delta.get("type") == "text_delta":
                    print(f"{ASSISTANT_COLOR}{delta['delta']}", end="", flush=True)

            if event.get("type") == "agent_settled":
                print("\n")
                print(RESET, end="", flush=True)
                break

    def teardown(self) -> int:
        """Terminate Pi and wait for it to exit.

        Returns:
            Pi's exit code. The process is killed if it does not stop within
            five seconds.
        """
        self.proc.terminate()

        try:
            exit_code = self.proc.wait(timeout=5)

            if exit_code != 0:
                warnings.warn(
                    f"Warning, Pi Agent subprocess exited with non-zero exit code {exit_code}"
                )

        except subprocess.TimeoutExpired:
            self.proc.kill()
            exit_code = self.proc.wait()

        return exit_code


if __name__ == "__main__":
    pi_agent = PiConnector(
        [
            "--mode",
            "rpc",
            "--no-session",
            "--no-skills",
            "--no-prompt-templates",
            "--no-context-files",
            "--tools",
            "read, web_search",
            # "--extension",
            # "pi-subagents",
            # "--extension",
            # "--tools read,web-search",
        ],
    )

    while True:
        try:
            print(USER_COLOR, end="", flush=True)
            message = "nothing"
            try:
                message = input(">> ")
                if message.strip() == "/quit":
                    break
            finally:
                print(RESET, end="", flush=True)
            pi_agent.chat(message)

        except KeyboardInterrupt:
            try:
                print(f"{ASSISTANT_COLOR}bye!")
            finally:
                print(RESET, end="", flush=True)
            break

    pi_agent.teardown()
