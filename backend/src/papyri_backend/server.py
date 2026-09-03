from __future__ import annotations

import os
from collections.abc import AsyncGenerator, Iterator
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import session
from .chat import answer_with_chat_stream, new_agent
from .exceptions import InvalidDecision, StaleDecision
from .settings import load_environment

load_environment()


# TODO: need more complex data models for tool results and stuff?
# -> only when we go beyond text. not necessary for now.
class ChatRequest(BaseModel):
    messages: list[Any] = Field(min_length=1)


class PausedAction(BaseModel):
    """One tool call a run is waiting for a decision on."""

    name: str
    args: dict[str, Any] = Field(default_factory=dict)
    allowed_decisions: list[str]


class InterruptView(BaseModel):
    """The decision a paused run needs before it can continue.

    ``id`` comes back with the client's reply, so a decision aimed at an
    interrupt that has since been answered is rejected rather than applied.
    """

    id: str
    actions: list[PausedAction]


class ChatResponse(BaseModel):
    text: str
    reasoning: str = ""
    interrupt: InterruptView | None = None


class ChatStreamEvent(ChatResponse):
    done: bool


def _cors_origins() -> list[str]:
    return [
        origin.strip()
        for origin in os.getenv("CORS_ORIGIN", "http://localhost:5173").split(",")
        if origin.strip()
    ]


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Own the process-local chat session for the server's lifetime."""
    session.start()
    try:
        yield
    finally:
        session.clear()


app = FastAPI(title="Papyri Backend", lifespan=lifespan)

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


@app.exception_handler(StaleDecision)
async def stale_decision_handler(_request: Request, exc: StaleDecision) -> JSONResponse:
    # The client's view of the conversation is out of date rather than wrong:
    # it should drop the dialog and re-read the current state, not retry.
    return JSONResponse(status_code=409, content={"error": str(exc)})


@app.exception_handler(InvalidDecision)
async def invalid_decision_handler(
    _request: Request, exc: InvalidDecision
) -> JSONResponse:
    return JSONResponse(status_code=422, content={"error": str(exc)})


@app.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}


@app.post("/new", response_model=ChatResponse)
async def new() -> JSONResponse | dict[str, str]:
    try:
        answer = new_agent()
        return answer
    except Exception as exc:
        message = str(exc) or "Unexpected error"
        return JSONResponse(status_code=500, content={"error": message})


def _prepare_chat(request: ChatRequest, response: Response) -> Iterator[dict[str, Any]]:
    """Prepare the run before FastAPI sends the streaming response headers."""
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return answer_with_chat_stream(request.messages)


ChatEvents = Annotated[Iterator[dict[str, Any]], Depends(_prepare_chat)]


@app.post("/chat")
def chat(events: ChatEvents) -> Iterator[ChatStreamEvent]:
    """Stream typed JSON Lines events using FastAPI's native support."""
    yield from events
