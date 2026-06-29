from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv


def load_environment() -> None:
    backend_env = Path(__file__).resolve().parents[2] / ".env"

    load_dotenv(backend_env)
    load_dotenv()
