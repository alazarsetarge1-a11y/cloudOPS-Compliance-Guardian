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

from pydantic import BaseModel, Field

from corrective.base import Action, Outcome
from detective.checks.base import Severity, Status


class FindingOut(BaseModel):
    """One compliance finding as the API returns it. Mirrors detective.Finding.

    status/severity are the domain enums (not bare str) so the published contract
    tells consumers exactly which values are possible — the frontend and MCP don't
    have to hardcode their own lists."""

    check_id: str
    resource_id: str
    resource_arn: str
    resource_type: str
    region: str
    account_id: str
    status: Status
    severity: Severity
    title: str
    detail: str
    remediation: str
    evidence: dict[str, Any]
    checked_at: datetime


class ComplianceScoreOut(BaseModel):
    """The rolled-up posture the dashboard's headline number reads. Mirrors the
    detective runner's summarize()."""

    total_findings: int
    by_status: dict[str, int]
    non_compliant_by_severity: dict[str, int]
    # None when there are no evaluable resources — ERROR resources are excluded
    # from the score, so "no data" is distinct from 0%.
    compliance_score_pct: float | None


class RemediationRequest(BaseModel):
    """What a caller sends to POST /remediations. Note what's ABSENT: no finding
    body, no status. The caller names the resource; the server re-derives whether
    it's actually a violation. `apply` is the gate — false (default) = dry run.

    The identifiers are length-bounded: an empty or multi-megabyte string is
    rejected (422) before it reaches the comparison loop or the 404 detail."""

    check_id: str = Field(min_length=1, max_length=64)
    resource_id: str = Field(min_length=1, max_length=256)
    apply: bool = False


class RemediationOut(BaseModel):
    """A remediation result as the API returns it. Mirrors corrective.RemediationResult."""

    check_id: str
    resource_id: str
    action: Action
    outcome: Outcome
    summary: str
    plan: dict[str, Any]
    executed_at: datetime
