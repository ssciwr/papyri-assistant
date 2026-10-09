"""Cover the shipped configs end to end, from file to constructed agent.

Nothing else in the suite reads the configs, so a config that cannot be loaded
looks exactly like a healthy repository: the server starts, /health answers, and
the failure only appears on the first real chat request. These tests close that
gap by doing at import time what the app does at request time.

No network is involved: the model object is only constructed, never called.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from papyri_backend.langchain_agent import LangChainAgent
from papyri_backend.utils import utils

CONFIGS = Path(__file__).resolve().parents[1] / "configs"
AGENT_CONFIG = CONFIGS / "default_langchain_agent.yaml"
OPENROUTER_CONFIG = CONFIGS / "openrouter_langchain_agent.yaml"
CLINE_CONFIG = CONFIGS / "cline_langchain_agent.yaml"


@pytest.fixture
def llm_env(monkeypatch) -> None:
    """Stand in for the deployment's LLM_* variables."""
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.setenv("LLM_API_URL", "http://localhost:9999/v1")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setattr(
        "papyri_backend.chat_models.httpx.get",
        lambda *_args, **_kwargs: type("Response", (), {"status_code": 404})(),
    )


def test_agent_config_file_exists() -> None:
    assert AGENT_CONFIG.is_file()


def test_agent_config_loads(llm_env) -> None:
    # Loading resolves the import paths and substitutes the environment, and is
    # where a prompt that reads like a dotted path used to be destroyed.
    config = utils.load_config(AGENT_CONFIG)

    assert config["system_prompt"].startswith("You are a concise")
    assert config["model"]["kwargs"]["model"] == "test-model"


@pytest.mark.parametrize("config_path", [AGENT_CONFIG, OPENROUTER_CONFIG, CLINE_CONFIG])
def test_agent_config_builds_an_agent(llm_env, config_path) -> None:
    # This is what the first request does, so a failure here is a 500 on the
    # first thing a user types.
    agent = LangChainAgent.from_config(config_path)

    assert agent.agent is not None
    assert agent.thread_id


@pytest.mark.parametrize(
    ("config_path", "base_url"),
    [
        (OPENROUTER_CONFIG, "https://openrouter.ai/api/v1/"),
        (CLINE_CONFIG, "https://api.cline.bot/api/v1/"),
    ],
)
def test_gateway_config_uses_standard_adapter_and_fixed_endpoint(
    llm_env, config_path, base_url
) -> None:
    from langchain_openai import ChatOpenAI

    config = utils.load_config(config_path)
    model = utils.build(config["model"])

    assert type(model) is ChatOpenAI
    assert model.model_name == "test-model"
    assert str(model.root_client.base_url) == base_url
    assert model.openai_api_key.get_secret_value() == "test-key"
    assert model.use_responses_api is False
    assert model.stream_usage is True
    assert "reasoning_effort" not in config["model"]["kwargs"]
    assert "profile" not in config["model"]["kwargs"]
