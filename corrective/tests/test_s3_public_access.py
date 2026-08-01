"""Tests for the S3 auto-remediation handler.

botocore's Stubber feeds canned SSM responses to a real client — no AWS, no
network. A tiny fake session hands the handler that stubbed client, since the
handler builds its own client internally (same pattern the detective tests use
for injecting a stubbed client into a pure function).
"""

import boto3
from botocore.stub import Stubber

from corrective.base import Action, Outcome
from corrective.remediations import s3_public_access as rem
from detective.checks.base import Finding, Severity, Status


def _finding(status: Status = Status.NON_COMPLIANT, bucket: str = "public-bucket") -> Finding:
    return Finding(
        check_id="s3-public-access",
        resource_id=bucket,
        resource_arn=f"arn:aws:s3:::{bucket}",
        resource_type="AWS::S3::Bucket",
        region="global",
        account_id="123456789012",
        status=status,
        severity=Severity.CRITICAL,
        title="Public bucket",
        detail="Block Public Access disabled",
        remediation="Re-enable Block Public Access.",
    )


class _FakeSession:
    """Returns a pre-stubbed client regardless of args, so we can Stubber the
    ssm client the handler creates internally."""

    def __init__(self, client):
        self._client = client

    def client(self, *args, **kwargs):
        return self._client


def _ssm():
    return boto3.client(
        "ssm",
        region_name="us-east-1",
        aws_access_key_id="testing",
        aws_secret_access_key="testing",
    )


def test_dry_run_plans_without_calling_aws():
    # session=None proves a dry run never builds a client or calls AWS.
    res = rem.remediate_s3_public_access(_finding(), None, apply=False)
    assert res.action is Action.AUTO_REMEDIATE
    assert res.outcome is Outcome.PLANNED
    assert res.plan["runbook"] == rem.RUNBOOK_NAME
    assert "execution_id" not in res.plan


def test_apply_starts_ssm_execution():
    ssm = _ssm()
    with Stubber(ssm) as stub:
        exec_id = "12345678-1234-1234-1234-123456789012"  # SSM ids are 36-char UUIDs
        stub.add_response(
            "start_automation_execution",
            {"AutomationExecutionId": exec_id},
            {"DocumentName": rem.RUNBOOK_NAME, "Parameters": {"BucketName": ["public-bucket"]}},
        )
        res = rem.remediate_s3_public_access(_finding(), _FakeSession(ssm), apply=True)
        stub.assert_no_pending_responses()
    assert res.outcome is Outcome.REMEDIATED
    assert res.plan["execution_id"] == exec_id


def test_apply_reports_ssm_error_as_failed():
    ssm = _ssm()
    with Stubber(ssm) as stub:
        stub.add_client_error(
            "start_automation_execution",
            service_error_code="AutomationDefinitionNotFoundException",
        )
        res = rem.remediate_s3_public_access(_finding(), _FakeSession(ssm), apply=True)
    assert res.outcome is Outcome.FAILED
    assert res.plan["error"] == "AutomationDefinitionNotFoundException"
