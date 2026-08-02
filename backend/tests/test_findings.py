"""Tests for GET /findings and GET /compliance-score (API-key protected).

Chained DI payoff: we override `get_findings` once to return canned findings, so
no route touches real AWS. The routes' own logic (auth, filtering, serialization,
validation, summarization) is tested offline and deterministically.
"""

import pytest
from app.dependencies import get_findings
from app.main import app
from fastapi.testclient import TestClient

from detective.checks.base import Finding, Severity, Status

API_KEY = "test-secret-key"
AUTH = {"X-API-Key": API_KEY}


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
    monkeypatch.setenv("CCG_API_KEY", API_KEY)
    app.dependency_overrides[get_findings] = lambda: CANNED
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_reads_require_api_key(client):
    # Missing key AND wrong key both -> 401 on the protected reads (a guard that
    # accepted any non-empty key would pass a missing-only test); /health open.
    assert client.get("/findings").status_code == 401
    assert client.get("/compliance-score").status_code == 401
    assert client.get("/findings", headers={"X-API-Key": "wrong"}).status_code == 401
    assert client.get("/compliance-score", headers={"X-API-Key": "wrong"}).status_code == 401
    assert client.get("/health").status_code == 200


def test_lists_all_findings(client):
    r = client.get("/findings", headers=AUTH)
    assert r.status_code == 200
    assert len(r.json()) == 3


def test_filter_by_status(client):
    r = client.get("/findings", params={"status": "NON_COMPLIANT"}, headers=AUTH)
    assert {f["check_id"] for f in r.json()} == {"s3-public-access", "security-groups"}


def test_filter_by_severity(client):
    r = client.get("/findings", params={"severity": "CRITICAL"}, headers=AUTH)
    body = r.json()
    assert len(body) == 1
    assert body[0]["check_id"] == "s3-public-access"


def test_invalid_status_is_rejected(client):
    r = client.get("/findings", params={"status": "BOGUS"}, headers=AUTH)
    assert r.status_code == 422


def test_compliance_score(client):
    body = client.get("/compliance-score", headers=AUTH).json()
    assert body["total_findings"] == 3
    assert body["by_status"]["NON_COMPLIANT"] == 2
    assert body["by_status"]["COMPLIANT"] == 1
    assert body["non_compliant_by_severity"]["CRITICAL"] == 1
    assert body["compliance_score_pct"] == 33.3


def test_score_is_none_when_only_errors(client):
    only_error = [_finding("s3-public-access", Status.ERROR, Severity.MEDIUM, "e1")]
    app.dependency_overrides[get_findings] = lambda: only_error
    body = client.get("/compliance-score", headers=AUTH).json()
    assert body["compliance_score_pct"] is None


def test_health_is_open(client):
    assert client.get("/health").json() == {"status": "ok"}
