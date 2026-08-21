from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .chat import answer_with_chat
from .exceptions import DecisionError, InvalidDecision, StaleDecision
from .settings import load_environment

load_environment()

# TODO:
# - build agent singleton for the moment. Session manager + user later
# -
# -
agent = None


# TODO: need more complex data models for tool results and stuff
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


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> JSONResponse | dict[str, str]:
    try:
        answer = await answer_with_chat(request.messages)
        return answer
    except DecisionError:
        # Left for the handlers above, which distinguish a stale decision from
        # an invalid one; collapsing both into a 500 here would lose that.
        raise
    except Exception as exc:
        message = str(exc) or "Unexpected error"
        return JSONResponse(status_code=500, content={"error": message})
