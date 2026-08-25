"""Cover the entry point that reads the server's settings out of the environment."""

from __future__ import annotations

import pytest

from papyri_backend import cli


# The truthy spellings are the ones an operator is likely to write in a .env
# file; the casing and the surrounding whitespace are part of the case, because
# a value that reads as "on" must not silently disable reloading.
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1", True),
        ("true", True),
        ("YES", True),
        (" on ", True),
        ("0", False),
        ("false", False),
        ("", False),
    ],
)
def test_env_bool_parses_enabled_values(
    monkeypatch, value: str, expected: bool
) -> None:
    monkeypatch.setenv("BACKEND_RELOAD", value)

    # "is" rather than "==": the flag is handed to uvicorn, which expects a bool
    # rather than something merely truthy.
    assert cli._env_bool("BACKEND_RELOAD") is expected


def test_env_bool_is_false_for_missing_env(monkeypatch) -> None:
    # An unset variable is the common case, and must not raise: it means "off".
    monkeypatch.delenv("BACKEND_RELOAD", raising=False)

    assert cli._env_bool("BACKEND_RELOAD") is False


def test_main_loads_environment_and_runs_uvicorn_with_env(monkeypatch) -> None:
    # Both fakes append to one list, so the assertion below pins the order as
    # well as the arguments: the .env file has to be loaded *before* uvicorn
    # starts, or the settings it reads would be the ones from the shell only.
    calls: list[object] = []

    def fake_load_environment() -> None:
        calls.append("load_environment")

    def fake_run(app_path: str, **kwargs: object) -> None:
        calls.append((app_path, kwargs))

    monkeypatch.setattr(cli, "load_environment", fake_load_environment)
    # Patching uvicorn.run is what keeps this a unit test: main() would
    # otherwise block on a real server.
    monkeypatch.setattr(cli.uvicorn, "run", fake_run)
    monkeypatch.setenv("BACKEND_HOST", "127.0.0.1")
    monkeypatch.setenv("BACKEND_PORT", "4321")
    monkeypatch.setenv("BACKEND_RELOAD", "yes")

    cli.main()

    # The port arrives as a string and has to reach uvicorn as an int.
    assert calls == [
        "load_environment",
        (
            "papyri_backend.server:app",
            {"host": "127.0.0.1", "port": 4321, "reload": True},
        ),
    ]


def test_main_uses_default_uvicorn_config(monkeypatch) -> None:
    # The counterpart of the test above: with nothing configured, the server
    # still has to come up on the documented host and port.
    run_calls: list[tuple[str, dict[str, object]]] = []

    monkeypatch.setattr(cli, "load_environment", lambda: None)
    monkeypatch.setattr(
        cli.uvicorn,
        "run",
        lambda app_path, **kwargs: run_calls.append((app_path, kwargs)),
    )
    # Cleared explicitly, because the developer running the suite may well have
    # these set in their own shell.
    monkeypatch.delenv("BACKEND_HOST", raising=False)
    monkeypatch.delenv("BACKEND_PORT", raising=False)
    monkeypatch.delenv("BACKEND_RELOAD", raising=False)

    cli.main()

    assert run_calls == [
        (
            "papyri_backend.server:app",
            {"host": "0.0.0.0", "port": 3001, "reload": False},
        )
    ]
