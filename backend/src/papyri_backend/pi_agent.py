import subprocess
import json
from typing import Any, Literal
from collections.abc import Mapping, Sequence
import warnings
import yaml
from dataclasses import dataclass
from pprint import pformat
import threading


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
            "/abort": self._process_command_abort,  # TODO: doesn't yet work
        }

        self.response_processors = {
            "new_session": self._process_response_new,
            "get_state": self._process_response_state,
            "get_messages": self._process_response_history,
            "get_available_models": self._process_response_models,
            "set_thinking_level": self._process_response_thinking,
            "set_model": self._process_response_model,
        }

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
        for event in self._read_events():
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

    def _process_command_steer(self, messages: list[str]):

        processed = {"type": "steer", "message": " ".join(messages)}
        return processed

    def _process_command_followup(self, messages: list[str]):
        processed = {"type": "follow_up", "message": " ".join(messages)}
        return processed

    def _process_command_thinking(self, messages: list[str]):
        processed = {"type": "set_thinking_level", "level": messages[1]}
        return processed

    def _process_command_abort(self, messages: list[str]):
        return {"type": "abort"}

    def _process_command_models(self, messages: list[str]):
        return {
            "type": "get_available_models",
        }

    def _process_command_model(self, messages: list[str]):
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
        return {
            "type": "new_session",
        }

    def _process_command_quit(self, messages: list[str]):
        return message

    def _process_command_history(self, messages: list[str]):
        return {
            "type": "get_messages",
        }

    def _process_command_state(self, messages: list[str]):
        return {
            "type": "get_state",
        }

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
        return f"Model has been switched to {message['name']}"

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
            The matching command payload or a 1payload.
        """
        normalized = input.strip().split(" ", 1)
        if normalized[0] in self.input_processors:
            processor = self.input_processors.get(normalized[0])
            if processor:
                processed = processor(normalized)
                return processed
            else:
                return normalized  # fails normally, only here to show failures atm
        else:
            return {
                "id": self.current_id,
                "type": "prompt",
                "message": input,
                "streamingBehavior": self.streaming_behavior,
            }

    def _send(self, input: str):
        """Send a serialized RPC request to the Pi process.

        Args:
            input: Raw user input to convert into a request.
            type: Requested RPC message type. Currently unused.
        """
        self.current_id += 1

        # TODO:
        # this must automatically switch to steering or follow up mode when the agent is running.
        # how can this be done? is there a way I can query the agent to check if it's still running?
        # we should make steer mode the default. we then implement a command to set it.
        to_send = self._process_input_message(input)
        print("processed input message: ", to_send)
        self.proc.stdin.write(json.dumps(to_send) + "\n")
        self.proc.stdin.flush()

    def _read_events(self):
        """Yield decoded RPC events from the Pi process standard output.

        Yields:
            Decoded JSON event payloads emitted by Pi.
        """
        for line in self.proc.stdout:
            yield json.loads(line)

    def _process_events(self):
        for event in self._read_events():
            if event.get("type") == "response":
                if event.get("success"):
                    if event.get("command") == "prompt":
                        continue
                    else:
                        result = self.response_processors[event.get("command")](
                            event.get("data")
                        )

                        if (
                            result
                            and isinstance(result, Sequence)
                            and not isinstance(result, str)
                        ):
                            for res in result:
                                print(f"{SYSTEM_COLOR}{res}", flush=True)
                                print("\n")
                        elif result:
                            print(f"{SYSTEM_COLOR}{result}")
                        else:
                            pass
                        break  # no further messages after the response to a command
                else:
                    print(event)
                    print(f"{SYSTEM_COLOR}Error, command {event.get('command')} failed")

            if event.get("type") == "message_update":
                delta = event.get("assistantMessageEvent", {})
                if delta.get("type") == "text_delta":
                    print(f"{ASSISTANT_COLOR}{delta['delta']}", end="", flush=True)

            if event.get("type") == "agent_settled":
                print("\n")
                print(RESET, end="", flush=True)
                break

    def chat(self, raw_message: str):
        """Send a message and render Pi's streaming response to standard output.

        Args:
            raw_message: The message to send to Pi.
        """
        self._send(raw_message)  # TODO: this needs auto-detect for different types

        if self._event_thread is None or not self._event_thread.is_alive():
            self._event_thread = threading.Thread(
                target=self._process_events,
                daemon=True,
            )
            self._event_thread.start()

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
