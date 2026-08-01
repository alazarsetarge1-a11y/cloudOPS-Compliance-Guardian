"""Auto-remediation for the detective ``security-groups`` check.

On ``apply=True`` this starts the SSM Automation runbook
``ccg-remediate-security-groups`` (deployed by infra/corrective/), which revokes
world-open ingress on sensitive ports from the flagged group. On a dry run it
returns the plan and touches nothing.

The runbook itself is guarded (re-checks the live group) and surgical (removes
only the world-open ranges) — see the YAML. This handler is the gated adapter
that decides *whether* to start it.

Note vs. the S3 handler: security groups are REGIONAL, so we start the automation
in ``finding.region`` (the group's real region), not a fixed region. The runbook +
role must exist in that region; infra/corrective deploys them single-region
(us-east-1), matching the rest of the project — a finding in another region would
come back FAILED with a clear "document not found" error rather than acting
somewhere unexpected.
"""

from __future__ import annotations

import boto3
from botocore.exceptions import ClientError

from corrective.base import BOTO_CONFIG, Action, Outcome, RemediationResult
from detective.checks.base import Finding

# MUST match aws_ssm_document.security_groups.name in infra/corrective/main.tf.
RUNBOOK_NAME = "ccg-remediate-security-groups"


def remediate_security_groups(
    finding: Finding, session: boto3.Session, *, apply: bool
) -> RemediationResult:
    sg_id = finding.resource_id
    region = finding.region  # security groups are regional — use the group's region
    plan = {
        "runbook": RUNBOOK_NAME,
        "api": "ec2:RevokeSecurityGroupIngress",
        "params": {
            "GroupId": sg_id,
            "Region": region,
            "scope": "world-open ingress on sensitive ports only",
        },
    }

    if not apply:
        return RemediationResult(
            check_id=finding.check_id,
            resource_id=sg_id,
            action=Action.AUTO_REMEDIATE,
            outcome=Outcome.PLANNED,
            summary=f"Would revoke world-open sensitive ingress on '{sg_id}' ({region}) via SSM runbook {RUNBOOK_NAME}.",
            plan=plan,
        )

    ssm = session.client("ssm", region_name=region, config=BOTO_CONFIG)
    try:
        resp = ssm.start_automation_execution(
            DocumentName=RUNBOOK_NAME,
            Parameters={"GroupId": [sg_id], "Region": [region]},
        )
    except ClientError as e:
        code = e.response["Error"]["Code"]
        return RemediationResult(
            check_id=finding.check_id,
            resource_id=sg_id,
            action=Action.AUTO_REMEDIATE,
            outcome=Outcome.FAILED,
            summary=f"Failed to start SSM runbook for '{sg_id}' ({region}): {code}.",
            plan={**plan, "error": code},
        )

    exec_id = resp["AutomationExecutionId"]
    return RemediationResult(
        check_id=finding.check_id,
        resource_id=sg_id,
        action=Action.AUTO_REMEDIATE,
        outcome=Outcome.REMEDIATED,
        summary=f"Started SSM runbook {RUNBOOK_NAME} on '{sg_id}' ({region}) (execution {exec_id}).",
        plan={**plan, "execution_id": exec_id},
    )
