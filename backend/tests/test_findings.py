"""Tests for GET /findings.

The payoff of dependency injection: we override `get_session` so no route touches
real AWS, and monkeypatch `run_all_checks` to return canned findings. The route's
own logic (filtering, serialization, validation) is then tested offline and
deterministically — the same discipline as the detective/corrective tests.
"""

import pytest
from app.dependencies import get_session
from app.main import app
from app.routers import findings as findings_router
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
def client(monkeypatch):
    # No real scan: canned findings instead of run_all_checks hitting AWS.
    monkeypatch.setattr(findings_router, "run_all_checks", lambda session: CANNED)
    # No real credentials: the session dependency is replaced wholesale.
    app.dependency_overrides[get_session] = lambda: None
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
    r = client.get("/findings", params={"status": "BOGUS"})
    assert r.status_code == 422


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}
