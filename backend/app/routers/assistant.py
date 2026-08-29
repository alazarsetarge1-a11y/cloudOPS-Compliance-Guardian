"""POST /assistant/ask — the AI best-practices assistant.

A thin transport over the transport-agnostic assistant service. Gated by the same
API key as the other reads/writes — an LLM endpoint is a cost/abuse vector, so it
is never left open. The service has no AWS access and no tools; FastAPI is the BFF
that holds ANTHROPIC_API_KEY server-side.
"""

from __future__ import annotations

import logging

import anthropic
from fastapi import APIRouter, Depends, HTTPException, status

from app.assistant.service import answer_question
from app.schemas import AssistantAsk, AssistantReply
from app.security import require_api_key

router = APIRouter()
logger = logging.getLogger("ccg.assistant")


@router.post(
    "/assistant/ask",
    response_model=AssistantReply,
    tags=["assistant"],
    dependencies=[Depends(require_api_key)],
)
def ask_assistant(body: AssistantAsk) -> dict:
    """Answer one AWS best-practice question. No account access; general guidance only."""
    try:
        answer = answer_question(body.question, [turn.model_dump() for turn in body.history])
    except anthropic.AnthropicError as exc:
        # Any Claude SDK failure (missing key, auth, rate-limit, 5xx, network). Never
        # surface the detail; return a clean 503 (the frontend shows an "unavailable"
        # state, like the backend-offline card).
        logger.warning("assistant call failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The assistant is temporarily unavailable.",
        ) from exc
    return {"answer": answer}
