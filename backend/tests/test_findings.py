"""Tests for GET /findings and GET /compliance-score.

The payoff of chained dependency injection: we override `get_findings` once to
return canned findings, so no route touches real AWS. The routes' own logic
(filtering, serialization, validation, summarization) is tested offline and
deterministically — the same discipline as the detective/corrective tests.
"""

import pytest
from app.dependencies import get_findings
from app.main import app
from fastapi.testclient import TestClient

from detective.checks.base import Finding, Severity, Status


def _finding(check_id, status, severity, rid):
    return Finding(
        check_id=check_id,
        resource_id=rid,
        resource_arn=f"arn:aws:s3:::{rid}",
        resource_type="AWS::S3::Bucket",
        region="global",
        account_id="123456789012",
        status=status,
        severity=severity,
        title="t",
        detail="d",
        remediation="fix",
    )


CANNED = [
    _finding("s3-public-access", Status.NON_COMPLIANT, Severity.CRITICAL, "b1"),
    _finding("iam-mfa", Status.COMPLIANT, Severity.LOW, "u1"),
    _finding("security-groups", Status.NON_COMPLIANT, Severity.HIGH, "sg1"),
]


@pytest.fixture
def client():
    # Inject canned findings in place of a real scan — no AWS, no credentials.
    app.dependency_overrides[get_findings] = lambda: CANNED
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_lists_all_findings(client):
    r = client.get("/findings")
    assert r.status_code == 200
    assert len(r.json()) == 3


def test_filter_by_status(client):
    r = client.get("/findings", params={"status": "NON_COMPLIANT"})
    assert {f["check_id"] for f in r.json()} == {"s3-public-access", "security-groups"}


def test_filter_by_severity(client):
    r = client.get("/findings", params={"severity": "CRITICAL"})
    body = r.json()
    assert len(body) == 1
    assert body[0]["check_id"] == "s3-public-access"


def test_invalid_status_is_rejected(client):
    # The enum-typed query param validates input before our code runs.
    assert client.get("/findings", params={"status": "BOGUS"}).status_code == 422


def test_compliance_score(client):
    body = client.get("/compliance-score").json()
    assert body["total_findings"] == 3
    assert body["by_status"]["NON_COMPLIANT"] == 2
    assert body["by_status"]["COMPLIANT"] == 1
    assert body["non_compliant_by_severity"]["CRITICAL"] == 1
    # 1 compliant of 3 evaluable -> 33.3%
    assert body["compliance_score_pct"] == 33.3


def test_score_is_none_when_only_errors(client):
    # summarize() excludes ERROR from the evaluable count, so the score is None
    # ("no evaluable resources"), not 0%. Guard that API contract.
    only_error = [_finding("s3-public-access", Status.ERROR, Severity.MEDIUM, "e1")]
    app.dependency_overrides[get_findings] = lambda: only_error
    assert client.get("/compliance-score").json()["compliance_score_pct"] is None


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}
