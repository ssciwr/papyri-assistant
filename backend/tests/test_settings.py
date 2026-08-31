"""Cover the loading of the .env files the backend reads its configuration from."""

from __future__ import annotations

from pathlib import Path

from papyri_backend import settings


def test_load_environment_loads_backend_env_before_default(monkeypatch) -> None:
    # The real load_dotenv is replaced by one that only records where it was
    # pointed, so the test says nothing about the developer's actual .env files.
    calls: list[Path | None] = []

    def fake_load_dotenv(path: Path | None = None) -> bool:
        calls.append(path)
        return True

    monkeypatch.setattr(settings, "load_dotenv", fake_load_dotenv)

    settings.load_environment()

    # Order is the point: the backend's own .env is loaded first, and the
    # search-from-the-working-directory call (path=None) only fills the gaps it
    # left, because load_dotenv does not overwrite what is already set.
    assert calls == [Path(settings.__file__).resolve().parents[2] / ".env", None]
