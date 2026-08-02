"""API-key auth for the mutating endpoints.

Used as a route guard: `dependencies=[Depends(require_api_key)]`. The check lives
in the app, so it's enforced identically locally and in production behind the ALB
— only the source of the key value changes (an env var locally; injected from
Secrets Manager / SSM into the ECS task in prod).
"""

from __future__ import annotations

import os
import secrets
from typing import Annotated

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

# auto_error=False so we own the failure responses (custom messages + the
# fail-closed 503 below) instead of FastAPI's default 403.
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(provided: Annotated[str | None, Security(_api_key_header)]) -> None:
    """Reject the request unless a valid X-API-Key header is present.

    Fails CLOSED: if the server has no CCG_API_KEY configured, the protected
    endpoint is disabled (503), never left open. A missing config must not
    silently drop authentication on the one endpoint that changes AWS.
    """
    expected = os.environ.get("CCG_API_KEY")
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Remediation is disabled: no API key configured on the server.",
        )
    # Constant-time compare so a wrong key can't be recovered via timing.
    if not provided or not secrets.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )
