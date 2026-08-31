"""Cover the check that config names refer to things that exist.

Neither ``interrupt_on`` nor ``FilesystemPermission`` validates its own names.
A misnamed tool never fires its approval prompt and a misnamed operation never
matches a path, so in both cases the guard the config asks for is silently
absent. These tests build agents from deliberately wrong configs, so they cover
the check itself rather than the state of any particular config file.
"""

from __future__ import annotations

import pytest
from deepagents import FilesystemPermission

from papyri_backend.langchain_agent import LangChainAgent

# The class, not its dotted path: load_config resolves paths, build
# constructs specs, and these tests start after the resolving step.
PERMISSION = FilesystemPermission


@pytest.fixture
def agent_kwargs():
    """Minimal working agent config, to be broken one field at a time."""
    from langchain_openai import ChatOpenAI

    return {
        "model": {
            "type": ChatOpenAI,
            "kwargs": {
                "model": "test-model",
                "base_url": "http://localhost:9999/v1",
                "api_key": "test-key",
            },
        },
        "tools": [],
    }


def test_a_valid_config_builds(agent_kwargs) -> None:
    # The baseline the negative cases are measured against: without this, a
    # check that rejects everything would look like a working check.
    agent_kwargs["interrupt_on"] = {"write_file": {"allowed_decisions": ["approve"]}}
    agent_kwargs["permissions"] = [
        {
            "type": PERMISSION,
            "kwargs": {
                "operations": ["read"],
                "paths": ["/workspace"],
                "mode": "allow",
            },
        }
    ]

    assert LangChainAgent(**agent_kwargs) is not None


def test_interrupt_on_a_tool_that_does_not_exist_is_rejected(agent_kwargs) -> None:
    # "edit" is the real mistake this catches: the tool is called "edit_file",
    # so the config read as though edits were gated on approval while they ran
    # unapproved.
    agent_kwargs["interrupt_on"] = {"edit": {"allowed_decisions": ["approve"]}}

    with pytest.raises(ValueError) as excinfo:
        LangChainAgent(**agent_kwargs)

    # The message has to name the offender and the alternatives, because the
    # whole failure mode is that the author believed the name was right.
    assert "edit" in str(excinfo.value)
    assert "edit_file" in str(excinfo.value)


def test_a_permission_operation_that_does_not_exist_is_rejected(agent_kwargs) -> None:
    # Only "read" and "write" exist. Naming tools here instead -- read_file,
    # delete, edit -- is accepted by the dataclass and then matches nothing, so
    # every rule written that way is inert, denies included.
    agent_kwargs["permissions"] = [
        {
            "type": PERMISSION,
            "kwargs": {
                "operations": ["read_file", "delete"],
                "paths": ["/secrets"],
                "mode": "deny",
            },
        }
    ]

    with pytest.raises(ValueError) as excinfo:
        LangChainAgent(**agent_kwargs)

    assert "read_file" in str(excinfo.value)
    assert "delete" in str(excinfo.value)


def test_tools_from_the_config_can_be_named_in_interrupt_on(agent_kwargs) -> None:
    # The valid names are not a fixed list: a tool the config supplies is as
    # real as a built-in one, so the check must read the agent's actual tools
    # rather than a hardcoded set of filesystem tool names.
    from papyri_backend.tools.sql import query_sql

    agent_kwargs["tools"] = [query_sql]
    agent_kwargs["interrupt_on"] = {"query_sql": {"allowed_decisions": ["approve"]}}

    assert LangChainAgent(**agent_kwargs) is not None
