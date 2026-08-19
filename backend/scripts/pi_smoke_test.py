import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from pathlib import Path

from papyri_backend import PiConnector

backend_env = Path("/mnt/dataLinux/Development/papyri-assistant/.env")
load_dotenv(backend_env)
load_dotenv()

# TODO
pi_agent = PiConnector()
