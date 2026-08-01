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

from corrective.base import BOTO_CONFIG, Action, Outcome, RemediationResult
from detective.checks.base import Finding

# MUST match aws_ssm_document.s3_public_access.name in infra/corrective/main.tf.
RUNBOOK_NAME = "ccg-remediate-s3-public-access"

# The runbook + role are deployed single-region (see infra/corrective). S3 buckets
# are global, so the finding's region is "global" — not a usable API region. We
# therefore start the automation in the region the document actually lives in.
REMEDIATION_REGION = "us-east-1"


def remediate_s3_public_access(
    finding: Finding, session: boto3.Session, *, apply: bool
) -> RemediationResult:
    bucket = finding.resource_id
    plan = {
        "runbook": RUNBOOK_NAME,
        "api": "s3:PutPublicAccessBlock",
        "params": {"BucketName": bucket, "PublicAccessBlockConfiguration": "all-true"},
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

    ssm = session.client("ssm", region_name=REMEDIATION_REGION, config=BOTO_CONFIG)
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

    exec_id = resp["AutomationExecutionId"]
    return RemediationResult(
        check_id=finding.check_id,
        resource_id=bucket,
        action=Action.AUTO_REMEDIATE,
        outcome=Outcome.REMEDIATED,
        summary=f"Started SSM runbook {RUNBOOK_NAME} on '{bucket}' (execution {exec_id}).",
        plan={**plan, "execution_id": exec_id},
    )
