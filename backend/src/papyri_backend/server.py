from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .chat import answer_with_chat
from .settings import load_environment

load_environment()


class ChatRequest(BaseModel):
    messages: list[Any] = Field(min_length=1)


class ChatResponse(BaseModel):
    text: str


def _cors_origins() -> list[str]:
    return [
        origin.strip()
        for origin in os.getenv("CORS_ORIGIN", "http://localhost:5173").split(",")
        if origin.strip()
    ]


app = FastAPI(title="Papyri Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _request: Request, _exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"error": "Expected a JSON body with a messages array."},
    )


@app.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> JSONResponse | dict[str, str]:
    try:
        return await answer_with_chat(request.messages)
    except Exception as exc:
        message = str(exc) or "Unexpected error"
        return JSONResponse(status_code=500, content={"error": message})
