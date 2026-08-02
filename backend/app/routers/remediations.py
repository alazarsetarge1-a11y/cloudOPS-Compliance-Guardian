"""`POST /remediations` — trigger a gated remediation for one finding.

The security-critical route. It does NOT trust a finding from the request body:
it takes only identifiers, re-derives the finding from a fresh scan, and acts
only if the server itself confirms the resource is currently NON_COMPLIANT. The
`apply` flag is the dry-run gate, and an API key guards the endpoint.
"""

from __future__ import annotations

from typing import Annotated

import boto3
from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_findings, get_session
from app.schemas import RemediationOut, RemediationRequest
from app.security import require_api_key
from corrective.remediator import remediate
from detective.checks.base import Finding, Status

router = APIRouter()


@router.post(
    "/remediations",
    response_model=RemediationOut,
    tags=["remediations"],
    dependencies=[Depends(require_api_key)],
)
def create_remediation(
    body: RemediationRequest,
    session: Annotated[boto3.Session, Depends(get_session)],
    findings: Annotated[list[Finding], Depends(get_findings)],
) -> dict:
    """Re-derive the named finding from a fresh scan, then remediate it (or plan).

    404 if there is no *current* NON_COMPLIANT finding for that check_id +
    resource_id — so a forged or stale request to "fix" a healthy resource does
    nothing. `apply=false` (default) returns the plan; `apply=true` executes.
    """
    match = next(
        (
            f
            for f in findings
            if f.check_id == body.check_id
            and f.resource_id == body.resource_id
            and f.status == Status.NON_COMPLIANT
        ),
        None,
    )
    if match is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No current NON_COMPLIANT finding for check_id '{body.check_id}' "
                f"on resource '{body.resource_id}'."
            ),
        )
    return remediate(match, session, apply=body.apply).to_dict()
