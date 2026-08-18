from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
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

    @abstractmethod
    def send(self, input: str):
        """Send user input to the agent process.

        Args:
            input: Raw user input to send.
        """
        ...

    @abstractmethod
    def _read_events(self):
        """Read events emitted by the agent process.

        Yields:
            Event payloads emitted by the agent.
        """
        ...

    @abstractmethod
    def chat(
        self,
    ):
        """Run the interactive prompt-and-response loop."""
        ...

    @abstractmethod
    def teardown(self) -> int:
        """Stop the underlying agent process.

        Returns:
            The process exit code.
        """
        ...
