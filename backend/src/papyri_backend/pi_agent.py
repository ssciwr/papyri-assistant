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
    def __init__(
        self,
        options_to_pass: list[str],
        subprocess_kwargs: dict[str, Any] | None = None,
    ): ...

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "AgentConnectorBase": ...

    def chat(self, raw_message: str): ...

    def teardown(self) -> int: ...


class PiConnector(AgentConnectorBase):
    def __init__(
        self,
        options_to_pass: list[str],
        subprocess_kwargs: dict[str, Any] | None = None,
    ):
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
        if message["cancelled"]:
            return ["new session cancelled"]
        return ["new session started"]

    def _process_state(self, message):
        formatted = yaml.safe_dump(
            message,
            sort_keys=False,
            default_flow_style=False,
            width=120,
        ).rstrip()
        return [formatted]

    def _process_history(self, message: dict[str, Any]):
        """print out conversation history in current session"""
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
        # A successful set_thinking_level response has no data payload.
        return ["thinking level set to medium"]

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "PiConnector":
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
        self.current_id += 1
        to_send = self._process_input_message(input)
        self.proc.stdin.write(json.dumps(to_send) + "\n")
        self.proc.stdin.flush()

    def _read_events(self):
        for line in self.proc.stdout:
            yield json.loads(line)

    def chat(self, raw_message: str):
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
