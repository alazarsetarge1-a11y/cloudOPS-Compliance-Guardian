"""Auto-remediation for the detective ``s3-public-access`` check.

On ``apply=True`` this starts the SSM Automation runbook
``ccg-remediate-s3-public-access`` (deployed by infra/corrective/), which
re-enables all four Block Public Access flags on the flagged bucket. On a dry run
it returns the plan and touches nothing.

The actual mutation lives in the runbook, not here — this handler is the gated
adapter that decides *whether* to start it. Keeping the AWS-changing logic in the
SSM document means every remediation run is recorded in CloudTrail + SSM
execution history, auditable independently of this code.
"""

from __future__ import annotations

import boto3
from botocore.exceptions import ClientError

from corrective.base import (
    BOTO_CONFIG,
    Action,
    Outcome,
    RemediationResult,
    remediation_region,
)
from detective.checks.base import Finding

# MUST match aws_ssm_document.s3_public_access.name in infra/corrective/main.tf.
RUNBOOK_NAME = "ccg-remediate-s3-public-access"


def remediate_s3_public_access(
    finding: Finding, session: boto3.Session, *, apply: bool
) -> RemediationResult:
    bucket = finding.resource_id
    # S3 buckets are global (finding.region == "global"), so we can't derive the
    # region from the finding — start the automation in the region the runbook is
    # deployed in (configurable via CCG_REMEDIATION_REGION).
    region = remediation_region()
    plan = {
        "runbook": RUNBOOK_NAME,
        "region": region,
        "ssm_parameters": {"BucketName": bucket},
        "effect": "enable S3 Block Public Access (all four flags)",
    }

    # Dry run: return the plan without building a client or calling AWS at all.
    if not apply:
        return RemediationResult(
            check_id=finding.check_id,
            resource_id=bucket,
            action=Action.AUTO_REMEDIATE,
            outcome=Outcome.PLANNED,
            summary=f"Would re-enable S3 Block Public Access on '{bucket}' via SSM runbook {RUNBOOK_NAME}.",
            plan=plan,
        )

    ssm = session.client("ssm", region_name=region, config=BOTO_CONFIG)
    try:
        resp = ssm.start_automation_execution(
            DocumentName=RUNBOOK_NAME,
            Parameters={"BucketName": [bucket]},
        )
    except ClientError as e:
        code = e.response["Error"]["Code"]
        return RemediationResult(
            check_id=finding.check_id,
            resource_id=bucket,
            action=Action.AUTO_REMEDIATE,
            outcome=Outcome.FAILED,
            summary=f"Failed to start SSM runbook for '{bucket}': {code}.",
            plan={**plan, "error": code},
        )

    # STARTED, not REMEDIATED: start_automation_execution only confirms SSM
    # accepted the request. The runbook can still fail during BlockPublicAccess or
    # VerifyBlocked. The caller reconciles the execution to REMEDIATED/FAILED via
    # get_automation_execution — we never record a success we haven't confirmed.
    exec_id = resp["AutomationExecutionId"]
    return RemediationResult(
        check_id=finding.check_id,
        resource_id=bucket,
        action=Action.AUTO_REMEDIATE,
        outcome=Outcome.STARTED,
        summary=f"Started SSM runbook {RUNBOOK_NAME} on '{bucket}' (execution {exec_id}); poll for terminal status.",
        plan={**plan, "execution_id": exec_id},
    )
