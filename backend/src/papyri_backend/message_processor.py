from .base import MessageProcessorBase
from collections.abc import Sequence


class MessageProcessorTerminal(MessageProcessorBase):
    """Render agent output as colorized terminal output."""

    USER_COLOR = "\033[36m"  # cyan
    ASSISTANT_COLOR = "\x1b[35m"  # magenta
    SYSTEM_COLOR = "\033[33m"  # amber
    RESET = "\033[0m"
    THINKING_STYLE = "\033[3;32m"  # italic green
    ERROR_COLOR = "\033[41m"

    def process_system_message(self, message):
        print(f"{self.SYSTEM_COLOR}{message}{self.RESET}")

    def process_tool_message(self, message): ...

    def process_answer_message(self, message):
        print(
            f"{self.ASSISTANT_COLOR}{message}{self.RESET}",
            end="",
            flush=True,
        )

    def set_base_input_options(self):
        print(self.USER_COLOR, end="", flush=True)

    def process_user_input(self, message) -> str:
        return input(f"{self.USER_COLOR}{message}{self.RESET}").strip()

    def process_input_failure(self, input):
        print(
            f"{self.ERROR_COLOR}{input} is not a known command.{self.RESET}",
            flush=True,
        )

    def process_error(self, message):
        print(f"{self.ERROR_COLOR}{message}{self.RESET}")

    def process_thinking_message(self, message):
        print(
            f"{self.THINKING_STYLE}{message}{self.RESET}",
            end="",
            flush=True,
        )

    def set_output_config(self):
        print(self.USER_COLOR, end="", flush=True)

    def reset_output_config(self):
        print(f"\n{self.RESET}", end="", flush=True)


class MessageProcessorFastAPI(MessageProcessorBase):
    def process_system_message(self, message): ...

    def process_tool_message(self, message): ...

    def process_answer_message(self, message): ...

    def process_user_input(self, message) -> str: ...

    def process_input_failure(self, input): ...

    def process_thinking_message(self, message): ...

    def process_error(self, message): ...
