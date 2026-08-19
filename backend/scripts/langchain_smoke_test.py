import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from pathlib import Path

from papyri_backend import LangChainAgent
from papyri_backend.langchain_agent import create_agent_from_config

backend_env = Path("/mnt/dataLinux/Development/papyri-assistant/.env")
load_dotenv(backend_env)
load_dotenv()


langchain_agent = create_agent_from_config(
    "/mnt/dataLinux/Development/papyri-assistant/backend/configs/default_langchain_agent.yaml"
)

# langchain_agent = LangChainAgent(
#     [],
#     {
#         "model": {
#             "type": ChatOpenAI,
#             "kwargs": {
#                 "model": os.environ["LLM_MODEL"],
#                 "api_key": os.environ.get("LLM_API_KEY", "EMPTY"),
#                 "base_url": os.getenv("LLM_API_URL"),
#             },
#         },
#         "system_prompt": "You are a concise, helpful assistant",
#         "interrupt_on": {"write_file": True},
#     },
# )

langchain_agent.run()
