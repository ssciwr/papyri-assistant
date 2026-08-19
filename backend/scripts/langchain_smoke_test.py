import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from pathlib import Path

from papyri_backend import LangChainAgent
from papyri_backend import LangChainAgent

from papyri_backend.langchain_agent import (
    create_agent_from_config as make_langchain_agent,
)


backend_env = Path("/mnt/dataLinux/Development/papyri-assistant/.env")
load_dotenv(backend_env)
load_dotenv()

config = str(
    Path(__file__).resolve().parents[2]
    / os.getenv("AGENT_CONFIG", "backend/configs/default_langchain_agent.yaml"),
)
print(config)
agent = make_langchain_agent(config)

agent.run()
