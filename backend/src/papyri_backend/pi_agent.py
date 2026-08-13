import subprocess
import json
from typing import Any
from pydantic import BaseModel, Field
import time
import warnings

class AgentConnectorBase:
    def __init__(self, options_to_pass: list[str], subprocess_kwargs: dict[str, Any]): ...

    def chat(self, raw_messages: list[Any]) -> dict[str, str]: ...

    def teardown(self) -> int: ...

class PiConnector(AgentConnectorBase):
    def __init__(self, options_to_pass: list[str], subprocess_kwargs: dict[str, Any]):
        self.proc = subprocess.Popen(
            ["pi", "--mode rpc",] + options_to_pass,
            **subprocess_kwargs
        )

    def _send(self, cmd):
        ...

    def _read_events(self):
        ...

    def chat(self, raw_messages: list[Any]) -> dict[str, str]: ...

    def teardown(self)->int:
        self.proc.terminate()

        try:
            exit_code = self.proc.wait(timeout=5)

            if exit_code != 0:
                warnings.warn(f"Warning, Pi Agent subprocess exited with non-zero exit code {exit_code}")

        except subprocess.TimeoutExpired:
            self.proc.kill()
            exit_code= self.proc.wait()

        return exit_code

if __name__ == "__main__":
