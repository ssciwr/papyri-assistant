from .base import BaseAgent
from langchain import agents


class LangChainAgent(BaseAgent):
    def __init__(self, options, kwargs):
        super().__init__(options, kwargs)

    def send(self, input: str): ...

    def _read_events(self): ...

    def chat(self): ...

    def teardown(self) -> int: ...
