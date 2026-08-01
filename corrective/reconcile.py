"""Reconcile a STARTED remediation to its terminal outcome.

Handlers return ``Outcome.STARTED`` right after kicking off an SSM Automation
execution — deliberately non-blocking, so a web request or MCP call doesn't hang
for the runbook to finish. This function closes that loop: given a STARTED
result, it reads the execution's terminal status and returns an updated
RemediationResult (REMEDIATED / FAILED, or still STARTED if it's mid-flight).

Transport-agnostic like everything else here, so the Step-4 backend and the MCP
tool both call it. *Persisting* the reconciled result to the dashboard's
remediation history is the backend's job (there's no datastore in this layer) —
this supplies the terminal-status read that persistence needs.
"""

from __future__ import annotations

from dataclasses import replace

import boto3

from corrective.base import BOTO_CONFIG, Outcome, RemediationResult, remediation_region

# SSM AutomationExecutionStatus -> our terminal Outcome. Anything not here
# (InProgress, Pending, Waiting, ...) means "not terminal yet".
_TERMINAL = {
    "Success": Outcome.REMEDIATED,
    "Failed": Outcome.FAILED,
    "TimedOut": Outcome.FAILED,
    "Cancelled": Outcome.FAILED,
    "CancelledBeforeExecution": Outcome.FAILED,
}


def reconcile(result: RemediationResult, session: boto3.Session) -> RemediationResult:
    """Return the terminal form of a STARTED result, or the result unchanged.

    Only STARTED results carrying an ``execution_id`` are reconcilable; anything
    else (PLANNED, NOTIFIED, SKIPPED, FAILED, already-REMEDIATED) is returned
    as-is and makes no AWS call.
    """
    exec_id = result.plan.get("execution_id")
    if result.outcome is not Outcome.STARTED or not exec_id:
        return result

    region = result.plan.get("region", remediation_region())
    ssm = session.client("ssm", region_name=region, config=BOTO_CONFIG)
    execution = ssm.get_automation_execution(AutomationExecutionId=exec_id)["AutomationExecution"]
    status = execution["AutomationExecutionStatus"]

    terminal = _TERMINAL.get(status)
    if terminal is None:
        return result  # still running — stays STARTED

    if terminal is Outcome.REMEDIATED:
        summary = f"SSM execution {exec_id} completed: {status}."
    else:
        reason = execution.get("FailureMessage", "")[:160]
        summary = f"SSM execution {exec_id} did not succeed: {status}. {reason}".strip()

    return replace(
        result, outcome=terminal, summary=summary, plan={**result.plan, "ssm_status": status}
    )
