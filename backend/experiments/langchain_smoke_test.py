import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from pathlib import Path

from papyri_backend.langchain_agent import (
    create_agent_from_config as make_langchain_deepagent,
)


backend_env = Path("/mnt/dataLinux/Development/papyri-assistant/.env")
load_dotenv(backend_env)
load_dotenv()

config = str(
    Path(__file__).resolve().parents[2]
    / os.getenv("AGENT_CONFIG", "backend/configs/default_langchain_agent.yaml"),
)
print(config)
agent = make_langchain_deepagent(config)

# The agent only answers one turn at a time now, the way the FastAPI handler
# calls it; the loop around it is this script's own.
while True:
    try:
        text = input(">> ").strip()
    except (EOFError, KeyboardInterrupt):
        break

    if not text or text == "/quit":
        break

    answer = agent.run_single_turn({"content": [{"text": text}]})

    if answer["reasoning"]:
        print(f"[reasoning] {answer['reasoning']}")

    print(answer["text"])

    if answer["interrupt"]:
        print(answer["interrupt"])

agent.teardown()
