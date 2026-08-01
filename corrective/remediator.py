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
    # Resolve the vetted remediation FIRST so the skip paths can report the
    # check_id's true Action. Action is a design-time fact ("what this check is
    # allowed to do"), not a function of the current status — an auto-remediable
    # bucket that happens to be COMPLIANT right now is still AUTO_REMEDIATE, and
    # the dashboard history must say so.
    spec = REGISTRY.get(finding.check_id)

    # Guard 1 — only known check_ids have a vetted remediation. An unknown one is
    # skipped, never guessed at (and NOTIFY is the honest label — we have no
    # registered capability for it).
    if spec is None:
        return RemediationResult(
            check_id=finding.check_id,
            resource_id=finding.resource_id,
            action=Action.NOTIFY,
            outcome=Outcome.SKIPPED,
            summary=f"Skipped — no remediation registered for check_id '{finding.check_id}'.",
        )

    # Guard 2 — only act on real violations. A COMPLIANT resource needs no fix,
    # and an ERROR means the detective layer could NOT evaluate it: "remediating"
    # unknown state is how automation breaks things. Never fix on ERROR.
    if finding.status != Status.NON_COMPLIANT:
        return RemediationResult(
            check_id=finding.check_id,
            resource_id=finding.resource_id,
            action=spec.action,
            outcome=Outcome.SKIPPED,
            summary=f"Skipped — finding status is {finding.status.value}, not NON_COMPLIANT.",
        )

    return spec.handler(finding, session, apply=apply)
