import subprocess
import json
from typing import Any
import warnings


class AgentConnectorBase:
    def __init__(
        self,
        options_to_pass: list[str],
        subprocess_kwargs: dict[str, Any] | None = None,
    ): ...

    def chat(self, raw_messages: list[Any]): ...

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

        super().__init__(options_to_pass, subprocess_kwargs)

    def _send(self, input: str, type: str = "prompt"):
        self.current_id += 1
        to_send = {"id": self.current_id, "type": type, "message": input}
        self.proc.stdin.write(json.dumps(to_send) + "\n")
        self.proc.stdin.flush()

    def _read_events(self):
        for line in self.proc.stdout:
            yield json.loads(line)

    def chat(self, raw_message: str):

        self._send(raw_message, type="prompt")

        for event in self._read_events():
            if event.get("type") == "message_update":
                delta = event.get("assistantMessageEvent", {})
                if delta.get("type") == "text_delta":
                    print(delta["delta"], end="", flush=True)

            if event.get("type") == "agent_end":
                print()
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
        ["--mode", "rpc", "--no-session"],
    )

    while True:
        try:
            message = input("what do you want to tell Pi?\n")
            pi_agent.chat(message)

        except KeyboardInterrupt:
            print("bye!")
            break

    pi_agent.teardown()
