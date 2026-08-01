"""Tests for the security-group auto-remediation handler.

Stubber feeds canned SSM responses to a real client via a tiny fake session, so
no AWS/network is touched. The runbook's own guard/surgical logic runs inside SSM
(aws:executeScript) and is validated live, not here — these tests cover the
handler's gate, its regional client selection, and the region-scope guard.
"""

import boto3
from botocore.stub import Stubber

from corrective.base import Action, Outcome
from corrective.remediations import security_groups as rem
from detective.checks.base import Finding, Severity, Status


def _finding(
    status: Status = Status.NON_COMPLIANT, sg: str = "sg-0abc123", region: str = "us-east-1"
) -> Finding:
    return Finding(
        check_id="security-groups",
        resource_id=sg,
        resource_arn=f"arn:aws:ec2:{region}:123456789012:security-group/{sg}",
        resource_type="AWS::EC2::SecurityGroup",
        region=region,
        account_id="123456789012",
        status=status,
        severity=Severity.HIGH,
        title="World-open SG",
        detail="Ingress from 0.0.0.0/0 allows: tcp/22.",
        remediation="Restrict ingress.",
        evidence={"world_open": ["tcp/22"]},
    )


class _FakeSession:
    """Returns a pre-stubbed client and records the region it was asked for, so a
    test can assert the handler selects the client region from the finding."""

    def __init__(self, client):
        self._client = client
        self.requested_region = None

    def client(self, *args, **kwargs):
        self.requested_region = kwargs.get("region_name")
        return self._client


def _ssm(region="us-east-1"):
    return boto3.client(
        "ssm",
        region_name=region,
        aws_access_key_id="testing",
        aws_secret_access_key="testing",
    )


def test_dry_run_plans_without_calling_aws():
    res = rem.remediate_security_groups(_finding(), None, apply=False)
    assert res.action is Action.AUTO_REMEDIATE
    assert res.outcome is Outcome.PLANNED
    assert res.plan["runbook"] == rem.RUNBOOK_NAME
    assert "execution_id" not in res.plan


def test_apply_starts_ssm_execution_in_findings_region(monkeypatch):
    # Point the deployed region at a NON-default region and use a finding there,
    # so the assertion proves the handler uses finding.region (not a hardcoded one).
    monkeypatch.setenv("CCG_REMEDIATION_REGION", "us-west-2")
    ssm = _ssm("us-west-2")
    sess = _FakeSession(ssm)
    with Stubber(ssm) as stub:
        exec_id = "12345678-1234-1234-1234-123456789012"
        stub.add_response(
            "start_automation_execution",
            {"AutomationExecutionId": exec_id},
            {
                "DocumentName": rem.RUNBOOK_NAME,
                "Parameters": {"GroupId": ["sg-0abc123"], "Region": ["us-west-2"]},
            },
        )
        res = rem.remediate_security_groups(_finding(region="us-west-2"), sess, apply=True)
        stub.assert_no_pending_responses()
    assert res.outcome is Outcome.STARTED
    assert res.plan["execution_id"] == exec_id
    assert sess.requested_region == "us-west-2"  # regional client selection


def test_finding_outside_deployed_region_is_skipped():
    # Default deployed region is us-east-1; a finding in another region must be a
    # clean, non-mutating SKIP rather than a cryptic SSM failure.
    res = rem.remediate_security_groups(_finding(region="eu-west-1"), None, apply=True)
    assert res.outcome is Outcome.SKIPPED
    assert res.action is Action.AUTO_REMEDIATE


def test_apply_reports_ssm_error_as_failed():
    ssm = _ssm()
    with Stubber(ssm) as stub:
        stub.add_client_error(
            "start_automation_execution",
            service_error_code="AutomationDefinitionNotFoundException",
        )
        res = rem.remediate_security_groups(_finding(), _FakeSession(ssm), apply=True)
    assert res.outcome is Outcome.FAILED
    assert res.plan["error"] == "AutomationDefinitionNotFoundException"
