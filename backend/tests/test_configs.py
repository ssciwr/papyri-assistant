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
EMBEDDER_CONFIG = CONFIGS / "default_langchain_embedder.yaml"
RETRIEVER_CONFIG = CONFIGS / "default_langchain_retriever.yaml"


@pytest.fixture
def llm_env(monkeypatch) -> None:
    """Stand in for the deployment's LLM_* variables."""
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.setenv("LLM_API_URL", "http://localhost:9999/v1")
    monkeypatch.setenv("LLM_API_KEY", "test-key")


@pytest.mark.parametrize(
    "path",
    [AGENT_CONFIG, EMBEDDER_CONFIG, RETRIEVER_CONFIG],
    ids=["agent", "embedder", "retriever"],
)
def test_config_file_exists(path: Path) -> None:
    assert path.is_file()


def test_agent_config_loads(llm_env) -> None:
    # Loading resolves the import paths and substitutes the environment, and is
    # where a prompt that reads like a dotted path used to be destroyed.
    config = utils.load_config(AGENT_CONFIG)

    assert config["system_prompt"].startswith("You are a concise")
    assert config["model"]["kwargs"]["model"] == "test-model"


def test_embedder_config_loads() -> None:
    config = utils.load_config(EMBEDDER_CONFIG)

    assert callable(config["embeddings"]["type"])
    assert config["embeddings"]["kwargs"]["model_kwargs"] == {"truncate_dim": 2000}
    assert config["store_kwargs"] == {
        "table_name": "embeddings",
        "schema_name": "public",
        "vector_size": 2000,
        "content_column": "content",
        "embedding_column": "embedding",
        "id_column": {
            "name": "chunk_id",
            "data_type": "TEXT",
            "nullable": False,
        },
        "metadata_columns": [
            {"name": "source", "data_type": "TEXT", "nullable": False},
            {
                "name": "transcription_id",
                "data_type": "TEXT",
                "nullable": False,
            },
        ],
        "metadata_json_column": "metadata",
    }


def test_retriever_config_loads() -> None:
    # Only loaded, not built: constructing the embeddings would fetch a
    # multi-gigabyte model.
    config = utils.load_config(RETRIEVER_CONFIG)

    assert callable(config["embeddings"]["type"])
    assert config["embeddings"]["kwargs"]["model_kwargs"] == {"truncate_dim": 2000}
    assert config["similarity_search_kwargs"] == {"k": 1}


def test_agent_config_builds_an_agent(llm_env) -> None:
    # This is what the first request does, so a failure here is a 500 on the
    # first thing a user types.
    agent = LangChainAgent.from_config(AGENT_CONFIG)

    assert agent.agent is not None
    assert agent.thread_id
