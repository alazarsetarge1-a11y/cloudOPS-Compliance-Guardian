"""The gated dispatcher — the one entrypoint the runner, FastAPI backend, and MCP
``trigger_remediation`` tool all call. All the safety lives here and in the
handlers, so no caller can route around it.
"""

from __future__ import annotations

import boto3

from corrective.base import Action, Outcome, RemediationResult
from corrective.registry import REGISTRY
from detective.checks.base import Finding, Status


def remediate(
    finding: Finding, session: boto3.Session, *, apply: bool = False
) -> RemediationResult:
    """Resolve a finding to its vetted remediation and run it (or plan it).

    ``apply=False`` (the default) never mutates AWS — it returns the plan. Only
    ``apply=True`` lets a handler execute a real change.
    """
    # Guard 1 — only act on real violations. A COMPLIANT resource needs no fix,
    # and an ERROR means the detective layer could NOT evaluate it: "remediating"
    # unknown state is how automation breaks things. Never fix on ERROR.
    if finding.status != Status.NON_COMPLIANT:
        return RemediationResult(
            check_id=finding.check_id,
            resource_id=finding.resource_id,
            action=Action.NOTIFY,
            outcome=Outcome.SKIPPED,
            summary=f"Skipped — finding status is {finding.status.value}, not NON_COMPLIANT.",
        )

    # Guard 2 — only known check_ids have a vetted remediation. An unknown one is
    # skipped, never guessed at.
    spec = REGISTRY.get(finding.check_id)
    if spec is None:
        return RemediationResult(
            check_id=finding.check_id,
            resource_id=finding.resource_id,
            action=Action.NOTIFY,
            outcome=Outcome.SKIPPED,
            summary=f"Skipped — no remediation registered for check_id '{finding.check_id}'.",
        )

    return spec.handler(finding, session, apply=apply)
