from __future__ import annotations

from pathlib import Path

from papyri_backend import settings


def test_load_environment_loads_backend_env_before_default(monkeypatch) -> None:
    calls: list[Path | None] = []

    def fake_load_dotenv(path: Path | None = None) -> bool:
        calls.append(path)
        return True

    monkeypatch.setattr(settings, "load_dotenv", fake_load_dotenv)

    settings.load_environment()

    assert calls == [Path(settings.__file__).resolve().parents[2] / ".env", None]
