import re

from .base import MessageProcessorBase
from collections.abc import Sequence
from typing import Any

# Models that reason inline mark the trace as ordinary answer text instead of
# emitting reasoning events. The tags are matched leniently because whitespace
# and casing vary between deployments.
_THINK_OPEN = re.compile(r"<\s*think\s*>", re.IGNORECASE)
_THINK_CLOSE = re.compile(r"</\s*think\s*>", re.IGNORECASE)


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

    def process_interrupt_message(self, option: str, indicator: str):
        self.process_system_message(option)

    def set_output_config(self):
        print(self.USER_COLOR, end="", flush=True)

    def reset_output_config(self):
        print(f"\n{self.RESET}", end="", flush=True)


class MessageProcessorFastAPI(MessageProcessorBase):
    """Collect agent output in buffers a request handler can hand back."""

    def __init__(self):
        self.full_answer = ""
        self.full_reasoning = ""
        self.full_error = ""
        self.full_options: dict[str, str] = {}

    def process_system_message(self, message: str):
        self.process_answer_message(message)

    def process_interrupt_message(self, option: str, indicator: str):
        self.full_options[option.strip()] = indicator.strip()

    def process_tool_message(self, message: dict[str, Any]):
        name = message.get("name")
        args = message.get("args") or {}
        body = "\n".join(f"{k}: {v}" for k, v in args.items())
        self.process_answer_message(f"\n\n````\nUsing tool: {name}\n{body}\n````\n\n")

    def process_answer_message(self, message: str):
        """Collect streamed answer text, splitting off an inline reasoning trace.
        Args:
            message: The next chunk of streamed answer text.
        """

        # The trace always comes first, so ``</think>`` is the single point at
        # which the stream switches from reasoning to answer. Text accumulates in
        # the answer buffer until then, which leaves a model that never reasons
        # inline with nothing to do. The tag is looked for in the accumulated
        # buffer rather than in the message, because a stream chunk can end in the
        # middle of it.

        self.full_answer += message

        close_tag = _THINK_CLOSE.search(self.full_answer)
        if close_tag is None:
            return

        # The opening tag is dropped when the model sent one; deployments whose
        # chat template pre-fills it start the trace without one.
        reasoning_part = _THINK_OPEN.sub("", self.full_answer[: close_tag.start()], 1)
        self.full_reasoning += reasoning_part
        self.full_answer = self.full_answer[close_tag.end() :]
        # self._reasoning_split = True

    def process_user_input(self, message) -> str:
        return message

    def process_input_failure(self, input):
        self.full_error = f"{input} is not a processable input"

    def process_thinking_message(self, message: str):
        self.full_reasoning += message

    def process_error(self, message: str):
        self.full_error += message

    def reset_output_config(self):
        self.full_answer = ""
        self.full_reasoning = ""
        self.full_error = ""
        self.full_options = {}
        # self._reasoning_split = False

    def set_output_config(self):
        pass
