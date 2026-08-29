"""Transport-agnostic AI assistant service.

Calls the Claude API to answer AWS best-practice questions. Deliberately has NO
AWS access, NO tools, and NO account data in context — the ARCHITECTURE is the
control: the model can only produce text, so a prompt injection cannot reach the
account (nothing to leak, nothing to trigger). The system prompt + input caps are
defense in depth. FastAPI is the BFF that holds ANTHROPIC_API_KEY server-side; the
browser never sees it.
"""

from __future__ import annotations

import logging
import os

import anthropic

from app.assistant.prompt import SYSTEM_PROMPT

logger = logging.getLogger("ccg.assistant")

# Built lazily on first use (NOT at import) so the app still starts when
# ANTHROPIC_API_KEY is absent — only the assistant call fails, and the route turns
# that into a 503. Reads the key from the environment (Secrets Manager in prod, like
# CCG_API_KEY); the browser never sees it.
_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


# Default to the most capable model; override with CCG_ASSISTANT_MODEL (e.g.
# claude-sonnet-5 or claude-haiku-4-5) to trade capability for cost on this simple
# Q&A without a code change.
_MODEL = os.environ.get("CCG_ASSISTANT_MODEL", "claude-opus-5")
_MAX_TOKENS = 1024  # a scoped answer, and a hard cost/abuse ceiling

_REFUSAL = (
    "I can't help with that. I answer general AWS security and compliance best-practice questions."
)


def answer_question(question: str, history: list[dict[str, str]]) -> str:
    """Answer one AWS best-practice question, given prior turns for context.

    `history` is a list of {"role": "user"|"assistant", "content": str} turns; the
    caller bounds its size. Returns the assistant's text (or a fixed refusal string
    if the model declines). Raises anthropic errors on API failure — the route maps
    those to a 503.
    """
    resp = _get_client().messages.create(
        model=_MODEL,
        max_tokens=_MAX_TOKENS,
        output_config={"effort": "low"},  # snappy + cheap for a Q&A; thinking stays adaptive
        # Frozen system prompt, prompt-cached: identical every request, so after the
        # first call the big prefix bills at ~0.1x. Volatile history/question sit
        # AFTER the cache breakpoint.
        system=[
            {"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}},
        ],
        messages=[*history, {"role": "user", "content": question}],
    )

    # Opus 5 safety classifiers can decline (HTTP 200, stop_reason="refusal") —
    # check before reading content, and return a fixed safe message.
    if resp.stop_reason == "refusal":
        logger.info("assistant declined a request (stop_reason=refusal)")
        return _REFUSAL

    return next((block.text for block in resp.content if block.type == "text"), "")
