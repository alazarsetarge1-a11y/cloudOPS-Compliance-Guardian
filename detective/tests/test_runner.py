"""Unit tests for the runner's aggregation logic — pure, no AWS."""

from detective.checks.base import Finding, Severity, Status
from detective.runner import _check_failed, summarize


def _finding(status: Status, severity: Severity = Severity.HIGH) -> Finding:
    return Finding(
        check_id="demo",
        resource_id="r",
        resource_arn="arn:aws:s3:::r",
        resource_type="AWS::S3::Bucket",
        region="global",
        account_id="123456789012",
        status=status,
        severity=severity,
        title="t",
        detail="d",
        remediation="fix",
    )


def test_summary_counts_and_score():
    findings = [
        _finding(Status.COMPLIANT),
        _finding(Status.COMPLIANT),
        _finding(Status.NON_COMPLIANT, Severity.CRITICAL),
        _finding(Status.ERROR),  # excluded from the score denominator
    ]
    s = summarize(findings)
    assert s["total_findings"] == 4
    assert s["by_status"]["COMPLIANT"] == 2
    assert s["by_status"]["NON_COMPLIANT"] == 1
    assert s["by_status"]["ERROR"] == 1
    assert s["non_compliant_by_severity"]["CRITICAL"] == 1
    # 2 compliant / (2 compliant + 1 non-compliant) = 66.7% — ERROR not counted
    assert s["compliance_score_pct"] == 66.7


def test_summary_empty_is_none_score():
    s = summarize([])
    assert s["total_findings"] == 0
    assert s["compliance_score_pct"] is None


def test_check_failure_becomes_error_finding():
    f = _check_failed("s3-public-access", "123456789012", ValueError("boom"))
    assert f.status == Status.ERROR
    assert f.check_id == "s3-public-access"
    assert "ValueError" in f.detail
    assert f.evidence["error_type"] == "ValueError"
