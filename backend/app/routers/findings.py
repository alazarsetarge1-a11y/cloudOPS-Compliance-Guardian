"""`/findings` — read the current compliance posture.

The route holds NO compliance logic: it wraps the detective service layer
(`run_all_checks`) and applies optional filters. That's the transport-agnostic
design paying off — the exact same function backs the MCP `get_violations` tool.
"""

from __future__ import annotations

from typing import Annotated

import boto3
from fastapi import APIRouter, Depends, Query

from app.dependencies import get_session
from app.schemas import FindingOut
from detective.checks.base import Severity, Status
from detective.runner import run_all_checks

router = APIRouter(tags=["findings"])


@router.get("/findings", response_model=list[FindingOut])
def list_findings(
    session: Annotated[boto3.Session, Depends(get_session)],
    status: Annotated[Status | None, Query(description="Filter by compliance status")] = None,
    severity: Annotated[Severity | None, Query(description="Filter by severity")] = None,
) -> list[dict]:
    """Run every detective check and return the findings, newest scan each call.

    `status` / `severity` are optional query filters. Because they're typed as the
    domain StrEnums, FastAPI validates them (a bad value 422s) and renders them as
    dropdowns in /docs — for free.
    """
    findings = run_all_checks(session)
    return [
        f.to_dict()
        for f in findings
        if (status is None or f.status == status) and (severity is None or f.severity == severity)
    ]
