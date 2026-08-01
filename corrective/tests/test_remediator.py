"""Tests for the gated dispatcher — the guards that protect every remediation.

No AWS: the dispatcher's own logic (status guard, unknown-check guard, dry-run
routing) never touches the network, and the notify handler makes no AWS call.
"""

from corrective.base import Action, Outcome
from corrective.remediator import remediate
from detective.checks.base import Finding, Severity, Status


def _finding(check_id: str, status: Status = Status.NON_COMPLIANT) -> Finding:
    return Finding(
        check_id=check_id,
        resource_id="r1",
        resource_arn="arn:aws:iam::123456789012:user/r1",
        resource_type="AWS::IAM::User",
        region="global",
        account_id="123456789012",
        status=status,
        severity=Severity.LOW,
        title="t",
        detail="d",
        remediation="fix it",
    )


def test_notify_dry_run_plans():
    res = remediate(_finding("iam-mfa"), None)
    assert res.action is Action.NOTIFY
    assert res.outcome is Outcome.PLANNED


def test_notify_apply_flags_human():
    res = remediate(_finding("iam-mfa"), None, apply=True)
    assert res.outcome is Outcome.NOTIFIED


def test_compliant_is_skipped():
    res = remediate(_finding("iam-mfa", Status.COMPLIANT), None, apply=True)
    assert res.outcome is Outcome.SKIPPED


def test_error_is_never_remediated_even_with_apply():
    """The core safety property: an un-evaluatable finding is never acted on,
    even when the caller explicitly asks to apply."""
    res = remediate(_finding("s3-public-access", Status.ERROR), None, apply=True)
    assert res.outcome is Outcome.SKIPPED


def test_unknown_check_id_is_skipped():
    res = remediate(_finding("made-up-check"), None, apply=True)
    assert res.outcome is Outcome.SKIPPED


def test_s3_routes_to_auto_remediate_on_dry_run():
    """A known auto-remediable check routes to its handler and, dry-run, returns
    a plan — proving registry wiring without any AWS call."""
    res = remediate(_finding("s3-public-access"), None)
    assert res.action is Action.AUTO_REMEDIATE
    assert res.outcome is Outcome.PLANNED
