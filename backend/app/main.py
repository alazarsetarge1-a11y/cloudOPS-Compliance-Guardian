"""FastAPI application entry point.

`app` is the ASGI application uvicorn serves. Domain routes are added as routers
in later pieces; for now the app carries only metadata and a health check.
"""

from __future__ import annotations

from fastapi import FastAPI

from app.routers import findings

# The title/version/summary aren't decoration — FastAPI publishes them in the
# OpenAPI spec and renders them at /docs, which is the API's contract.
app = FastAPI(
    title="Cloud Compliance Guardian API",
    version="0.1.0",
    summary="REST access to AWS compliance findings and gated remediation.",
)

# Domain routes live in routers/ and are mounted here. main.py stays a thin
# composition root: app metadata + wiring, no business logic.
app.include_router(findings.router)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    """Liveness probe. Deliberately makes NO AWS calls, so it reports the web
    process is up independently of whether credentials are configured — that
    separation is what lets a load balancer / ECS restart a hung container
    without being confused by an unrelated AWS outage."""
    return {"status": "ok"}
