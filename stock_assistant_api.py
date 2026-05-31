"""
Stock Assistant web app.

A single FastAPI service that serves the chat UI (static/index.html) and the
/analyze endpoint that runs the agent pipeline. No separate frontend build.
"""

import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from stock_orchestrator import answer_question_sync

app = FastAPI(title="Stock Assistant", version="1.0.0")


class StockRequest(BaseModel):
    question: str


class StockResponse(BaseModel):
    response: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/analyze", response_model=StockResponse)
def analyze(request: StockRequest) -> StockResponse:
    response = answer_question_sync(request.question)
    return StockResponse(response=response)


# Serve the chat UI. Mounted last so the API routes above take precedence.
_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="static")
