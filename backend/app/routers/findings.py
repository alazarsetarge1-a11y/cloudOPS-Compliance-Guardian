"""Read the current compliance posture: `/findings` and `/compliance-score`.

Neither route holds compliance logic — they consume the `get_findings`
dependency (a full detective scan) and either serialize/filter it or roll it up
via the runner's `summarize()`. Same functions back the MCP tools later.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_findings
from app.schemas import ComplianceScoreOut, FindingOut
from app.security import require_api_key
from detective.checks.base import Finding, Severity, Status
from detective.runner import summarize

# Router-level auth: findings expose the account's misconfigurations + ARNs — a
# threat map — so both read routes require the API key. Only /health (in main.py)
# is unauthenticated.
router = APIRouter(dependencies=[Depends(require_api_key)])


@router.get("/findings", response_model=list[FindingOut], tags=["findings"])
def list_findings(
    findings: Annotated[list[Finding], Depends(get_findings)],
    status: Annotated[Status | None, Query(description="Filter by compliance status")] = None,
    severity: Annotated[Severity | None, Query(description="Filter by severity")] = None,
) -> list[dict]:
    """Return the current findings. `status` / `severity` are optional filters;
    typing them as the domain StrEnums gives validation (bad value → 422) and
    /docs dropdowns for free."""
    return [
        f.to_dict()
        for f in findings
        if (status is None or f.status == status) and (severity is None or f.severity == severity)
    ]


@router.get("/compliance-score", response_model=ComplianceScoreOut, tags=["score"])
def compliance_score(findings: Annotated[list[Finding], Depends(get_findings)]) -> dict:
    """Roll the findings up into counts + a compliance score — the dashboard's
    headline number. Wraps the runner's summarize()."""
    return summarize(findings)
