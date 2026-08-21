from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    """Define the interface for connectors that communicate with AI agents."""

    def __init__(
        self,
        options_to_pass: list[str],
        kwargs: dict[str, Any] | None = None,
    ):
        """Initialize a connector with agent command-line options.

        Args:
            options_to_pass: Command-line options passed to the agent process.
            kwargs: Optional keyword arguments for creating the process.
        """
        ...

    @abstractmethod
    def send_message(self, input: str):
        """send_message user input to the agent process.

        Args:
            input: Raw user input to send_message.
        """
        ...

    @abstractmethod
    def get_answers(self):
        """Read events emitted by the agent process.

        Yields:
            Event payloads emitted by the agent.
        """
        ...

    @abstractmethod
    def teardown(self) -> int:
        """Stop the underlying agent process.

        Returns:
            The process exit code.
        """
        ...

    @abstractmethod
    def run_single_turn(self, message) -> dict[str, str]:
        """Connection point to fastAPI

        Args:
            message: A single incoming chat message.

        Returns:
            The agent's ``text`` answer and its ``reasoning`` trace, either of
            which may be empty.
        """
        ...
