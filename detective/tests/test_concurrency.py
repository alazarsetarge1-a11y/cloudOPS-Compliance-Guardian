"""Tests for the scan's concurrency plumbing — no AWS, just fakes.

The fan-out lives in two places: `base.scan_regions` overlaps the per-region
calls inside a regional check, and `runner.run_all_checks` overlaps the checks
themselves. Both are built so the *behavior* (which findings come back, what
happens when something fails) is identical to the old serial code — only the
wall-clock time changes. These tests pin that behavior without touching AWS:
`enabled_regions`/`make_client` and the check registry are monkeypatched, so the
pools run real threads over fake clients.
"""

from __future__ import annotations

import pytest

from detective import runner
from detective.checks import base
from detective.checks.base import Finding, Severity, Status


def _finding(region: str = "global", status: Status = Status.COMPLIANT) -> Finding:
    return Finding(
        check_id="t",
        resource_id="r",
        resource_arn="arn",
        resource_type="T",
        region=region,
        account_id="123456789012",
        status=status,
        severity=Severity.LOW,
        title="t",
        detail="d",
        remediation="fix",
    )


# --- base.scan_regions -------------------------------------------------------


def test_scan_regions_covers_every_region_with_its_own_client(monkeypatch):
    regions = ["us-east-1", "eu-west-1", "ap-south-1"]
    monkeypatch.setattr(base, "enabled_regions", lambda _session: regions)
    # Fake client == the region it was built for, so we can assert each region's
    # scan ran against the client created for that region.
    monkeypatch.setattr(base, "make_client", lambda _s, _svc, **kw: kw["region_name"])

    seen: list[tuple[str, str]] = []

    def scan_region(region: str, client: str) -> list[Finding]:
        seen.append((region, client))
        return [_finding(region)]

    findings = base.scan_regions(object(), "ec2", scan_region)

    assert {r for r, _ in seen} == set(regions)  # every region visited exactly
    assert all(region == client for region, client in seen)  # right client per region
    assert {f.region for f in findings} == set(regions)  # all regions' findings aggregated


def test_scan_regions_propagates_a_failing_region(monkeypatch):
    # One region raising must bubble out of the helper — that's how the runner
    # gets to record a single ERROR finding for the whole check, exactly as the
    # old serial loop did when a region call raised.
    monkeypatch.setattr(base, "enabled_regions", lambda _session: ["us-east-1", "eu-west-1"])
    monkeypatch.setattr(base, "make_client", lambda _s, _svc, **kw: kw["region_name"])

    def scan_region(region: str, _client: str) -> list[Finding]:
        if region == "eu-west-1":
            raise RuntimeError("region boom")
        return [_finding(region)]

    with pytest.raises(RuntimeError, match="region boom"):
        base.scan_regions(object(), "ec2", scan_region)


# --- runner.run_all_checks (concurrent) --------------------------------------


class _FakeCheck:
    def __init__(self, check_id, *, result=None, exc=None):
        self.CHECK_ID = check_id
        self._result = result or []
        self._exc = exc

    def run(self, _session):
        if self._exc is not None:
            raise self._exc
        return self._result


def test_run_all_checks_aggregates_and_preserves_order(monkeypatch):
    monkeypatch.setattr(runner, "account_id_of", lambda _s: "123456789012")
    checks = [
        _FakeCheck("a", result=[_finding("r1", Status.COMPLIANT)]),
        _FakeCheck("b", result=[_finding("r2", Status.NON_COMPLIANT)]),
        _FakeCheck("c", result=[_finding("r3", Status.COMPLIANT)]),
    ]
    monkeypatch.setattr(runner, "CHECKS", checks)

    findings = runner.run_all_checks(object())

    # Output stays in CHECKS order even though the checks ran concurrently.
    assert [f.region for f in findings] == ["r1", "r2", "r3"]


def test_run_all_checks_isolates_a_crashing_check(monkeypatch):
    monkeypatch.setattr(runner, "account_id_of", lambda _s: "123456789012")
    checks = [
        _FakeCheck("good", result=[_finding("ok", Status.COMPLIANT)]),
        _FakeCheck("bad", exc=RuntimeError("boom")),
    ]
    monkeypatch.setattr(runner, "CHECKS", checks)

    findings = runner.run_all_checks(object())

    assert findings[0].status == Status.COMPLIANT  # good check's finding survives
    assert findings[-1].status == Status.ERROR  # bad check became one ERROR finding
    assert findings[-1].check_id == "bad"
    assert findings[-1].evidence["error_type"] == "RuntimeError"
