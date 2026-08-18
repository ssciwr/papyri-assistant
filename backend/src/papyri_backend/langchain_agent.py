from .base import BaseAgent
from deepagents import create_deep_agent
from langchain.agents.middleware import TodoListMiddleware


class LangChainAgent(BaseAgent):
    def __init__(self, options, kwargs):
        super().__init__(options, kwargs)

        self.agent = create_deep_agent(
            *options,
            **kwargs,
        )

    def send_message(self, input: str): ...

    def get_answers(self): ...

    def chat(self): ...

    def teardown(self) -> int: ...
