"""Notify-and-track handler — for findings that cannot be safely auto-fixed.

Three of the five checks land here, and each for a concrete reason:

* ``rds-encryption`` — encryption at rest cannot be toggled on a live RDS
  instance. The only real fix is snapshot -> encrypted copy -> restore ->
  repoint clients: too destructive to run unattended.
* ``iam-mfa`` — you cannot enroll another principal's MFA device on their
  behalf; the user must do it.
* ``tag-compliance`` — the *values* of the missing tags (owner, cost-center)
  cannot be inferred, only the fact that they're absent.

So the honest action is to flag a human, not to fake a fix. Today "notify"
returns a structured intent that the backend will persist and the dashboard will
surface; wiring it to SNS/Slack is a later enhancement — the return shape already
carries everything such a notification would need (ARN, severity, reason).
"""

from __future__ import annotations

import boto3

from corrective.base import Action, Outcome, RemediationResult
from detective.checks.base import Finding


def notify(finding: Finding, session: boto3.Session, *, apply: bool) -> RemediationResult:
    """Record the intent to flag a human. Makes no AWS mutation in either mode,
    so ``apply`` only changes the *outcome label* (PLANNED vs NOTIFIED), not the
    behavior — there is nothing to guard against here."""
    outcome = Outcome.NOTIFIED if apply else Outcome.PLANNED
    verb = "Flagged" if apply else "Would flag"
    return RemediationResult(
        check_id=finding.check_id,
        resource_id=finding.resource_id,
        action=Action.NOTIFY,
        outcome=outcome,
        summary=(
            f"{verb} {finding.resource_id} for human review — "
            f"{finding.check_id} is not safely auto-remediable."
        ),
        plan={
            "kind": "notify",
            "resource_arn": finding.resource_arn,
            "severity": finding.severity.value,
            "reason": finding.remediation,
        },
    )
