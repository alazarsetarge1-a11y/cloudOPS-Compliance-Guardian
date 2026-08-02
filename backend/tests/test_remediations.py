"""Tests for POST /remediations — the gated, API-key-protected mutating endpoint.

Offline: get_findings is overridden with canned findings and get_session with a
dummy, so the route's auth, trust model (re-derivation), and gate are all tested
without AWS. apply=True is exercised only on a NOTIFY finding (no AWS call);
auto-fix apply paths are validated live + in the corrective tests.
"""

import pytest
from app.dependencies import get_findings, get_session
from app.main import app
from app.security import require_api_key
from fastapi import HTTPException
from fastapi.testclient import TestClient

from detective.checks.base import Finding, Severity, Status

API_KEY = "test-secret-key"


def _finding(check_id, status, severity, rid):
    return Finding(
        check_id=check_id,
        resource_id=rid,
        resource_arn=f"arn:aws:x:::{rid}",
        resource_type="AWS::X::Y",
        region="us-east-1",
        account_id="123456789012",
        status=status,
        severity=severity,
        title="t",
        detail="d",
        remediation="fix",
    )


CANNED = [
    _finding("s3-public-access", Status.NON_COMPLIANT, Severity.HIGH, "b1"),
    _finding("rds-encryption", Status.NON_COMPLIANT, Severity.MEDIUM, "db1"),
    _finding("iam-mfa", Status.COMPLIANT, Severity.LOW, "u-ok"),
]


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("CCG_API_KEY", API_KEY)
    app.dependency_overrides[get_findings] = lambda: CANNED
    app.dependency_overrides[get_session] = lambda: None
    yield TestClient(app)
    app.dependency_overrides.clear()


def _post(client, check_id, resource_id, apply=False, key=API_KEY):
    headers = {"X-API-Key": key} if key is not None else {}
    return client.post(
        "/remediations",
        json={"check_id": check_id, "resource_id": resource_id, "apply": apply},
        headers=headers,
    )


def test_missing_api_key_is_401(client):
    assert _post(client, "s3-public-access", "b1", key=None).status_code == 401


def test_wrong_api_key_is_401(client):
    assert _post(client, "s3-public-access", "b1", key="nope").status_code == 401


def test_server_without_key_configured_is_503(client, monkeypatch):
    # Fail-closed: no CCG_API_KEY on the server -> endpoint disabled, not open.
    monkeypatch.delenv("CCG_API_KEY", raising=False)
    assert _post(client, "s3-public-access", "b1").status_code == 503


def test_dry_run_returns_plan(client):
    r = _post(client, "s3-public-access", "b1", apply=False)
    assert r.status_code == 200
    body = r.json()
    assert body["action"] == "AUTO_REMEDIATE"
    assert body["outcome"] == "PLANNED"


def test_apply_on_notify_finding(client):
    r = _post(client, "rds-encryption", "db1", apply=True)
    assert r.status_code == 200
    assert r.json()["outcome"] == "NOTIFIED"


def test_unknown_resource_is_404(client):
    assert _post(client, "s3-public-access", "does-not-exist").status_code == 404


def test_compliant_resource_is_not_remediated(client):
    # Trust model: the resource exists but is COMPLIANT, so there's nothing to
    # remediate — a forged "fix this" request gets 404, not a mutation.
    assert _post(client, "iam-mfa", "u-ok", apply=True).status_code == 404


def test_forged_status_in_body_is_ignored(client):
    # Even if the caller injects a status claiming the resource is bad, the server
    # re-derives from the scan — iam-mfa/u-ok is COMPLIANT, so still 404. This
    # pins the trust model against an extra unexpected body field.
    r = client.post(
        "/remediations",
        json={
            "check_id": "iam-mfa",
            "resource_id": "u-ok",
            "apply": True,
            "status": "NON_COMPLIANT",
        },
        headers={"X-API-Key": API_KEY},
    )
    assert r.status_code == 404


def test_non_ascii_api_key_is_401_not_500(monkeypatch):
    # A real latin-1 header can carry a non-ASCII byte that reaches the guard; it
    # must yield 401, not a 500 from compare_digest choking on a non-ASCII str.
    # (httpx's TestClient can't send non-ASCII headers, so we exercise the guard
    # function directly.)
    monkeypatch.setenv("CCG_API_KEY", "expected-key")
    with pytest.raises(HTTPException) as exc:
        require_api_key("café-clé")
    assert exc.value.status_code == 401
