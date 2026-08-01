"""Tests for the STARTED -> terminal reconciler.

Stubber feeds canned get_automation_execution responses; no AWS/network.
"""

import boto3
from botocore.stub import Stubber

from corrective.base import Action, Outcome, RemediationResult
from corrective.reconcile import reconcile

EXEC_ID = "12345678-1234-1234-1234-123456789012"


def _started() -> RemediationResult:
    return RemediationResult(
        check_id="s3-public-access",
        resource_id="public-bucket",
        action=Action.AUTO_REMEDIATE,
        outcome=Outcome.STARTED,
        summary="started",
        plan={"execution_id": EXEC_ID, "region": "us-east-1"},
    )


class _FakeSession:
    def __init__(self, client):
        self._client = client

    def client(self, *args, **kwargs):
        return self._client


def _ssm():
    return boto3.client(
        "ssm", region_name="us-east-1", aws_access_key_id="t", aws_secret_access_key="t"
    )


def _stub_status(stub, status, failure=None):
    exe = {"AutomationExecutionId": EXEC_ID, "AutomationExecutionStatus": status}
    if failure:
        exe["FailureMessage"] = failure
    stub.add_response(
        "get_automation_execution", {"AutomationExecution": exe}, {"AutomationExecutionId": EXEC_ID}
    )


def test_success_becomes_remediated():
    ssm = _ssm()
    with Stubber(ssm) as stub:
        _stub_status(stub, "Success")
        res = reconcile(_started(), _FakeSession(ssm))
    assert res.outcome is Outcome.REMEDIATED
    assert res.plan["ssm_status"] == "Success"


def test_failed_becomes_failed_with_reason():
    ssm = _ssm()
    with Stubber(ssm) as stub:
        _stub_status(stub, "Failed", failure="step X denied")
        res = reconcile(_started(), _FakeSession(ssm))
    assert res.outcome is Outcome.FAILED
    assert "step X denied" in res.summary


def test_in_progress_stays_started():
    ssm = _ssm()
    with Stubber(ssm) as stub:
        _stub_status(stub, "InProgress")
        res = reconcile(_started(), _FakeSession(ssm))
    assert res.outcome is Outcome.STARTED


def test_non_started_result_is_returned_untouched_without_aws():
    # A PLANNED result has no execution to reconcile; session=None proves no call.
    planned = RemediationResult(
        check_id="s3-public-access",
        resource_id="b",
        action=Action.AUTO_REMEDIATE,
        outcome=Outcome.PLANNED,
        summary="planned",
        plan={},
    )
    assert reconcile(planned, None) is planned
