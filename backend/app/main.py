"""FastAPI application entry point.

`app` is the ASGI application uvicorn serves. Domain routes are added as routers
in later pieces; for now the app carries only metadata and a health check.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import findings, remediations

# The title/version/summary aren't decoration — FastAPI publishes them in the
# OpenAPI spec and renders them at /docs, which is the API's contract.
app = FastAPI(
    title="Cloud Compliance Guardian API",
    version="0.1.0",
    summary="REST access to AWS compliance findings and gated remediation.",
)

# CORS: a browser blocks a page from calling an API on a different origin unless
# the API opts in. The React dev server (localhost:5173) is a different origin
# from the API (localhost:8000), so we allow it explicitly. Origins are an
# allow-LIST from env (never "*"), and we allow only the methods + headers the
# app actually uses — including the X-API-Key auth header.
_cors_origins = [
    o.strip()
    for o in os.environ.get("CCG_CORS_ORIGINS", "http://localhost:5173").split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["X-API-Key", "Content-Type"],
)

# Domain routes live in routers/ and are mounted here. main.py stays a thin
# composition root: app metadata + wiring, no business logic.
app.include_router(findings.router)
app.include_router(remediations.router)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    """Liveness probe. Deliberately makes NO AWS calls, so it reports the web
    process is up independently of whether credentials are configured — that
    separation is what lets a load balancer / ECS restart a hung container
    without being confused by an unrelated AWS outage."""
    return {"status": "ok"}
