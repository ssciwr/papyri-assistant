from __future__ import annotations

import os

import uvicorn

from .settings import load_environment


def main() -> None:
    load_environment()

    uvicorn.run(
        "papyri_backend.server:app",
        host=os.getenv("BACKEND_HOST", "0.0.0.0"),
        port=int(os.getenv("BACKEND_PORT", "3001")),
        reload=_env_bool("BACKEND_RELOAD"),
    )


def _env_bool(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}
