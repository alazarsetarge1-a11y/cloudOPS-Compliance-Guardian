"""Pydantic response models — the typed API contract FastAPI publishes as OpenAPI.

Kept deliberately SEPARATE from the service-layer dataclasses (detective
`Finding`, corrective `RemediationResult`): those are the internal domain shape,
these are the external API shape. Decoupling them means an internal refactor
can't silently change the public contract the frontend + MCP depend on. The
route converts one to the other with `.to_dict()`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class FindingOut(BaseModel):
    """One compliance finding as the API returns it. Mirrors detective.Finding."""

    check_id: str
    resource_id: str
    resource_arn: str
    resource_type: str
    region: str
    account_id: str
    status: str
    severity: str
    title: str
    detail: str
    remediation: str
    evidence: dict[str, Any]
    checked_at: datetime
