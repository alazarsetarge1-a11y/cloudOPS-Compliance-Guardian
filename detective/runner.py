"""Detective runner — the aggregator that adapters call.

`run_all_checks(session)` invokes every registered check and returns one combined
`list[Finding]`. Two things worth understanding:

1. It is deliberately **resilient**. If a single check raises, the runner turns
   that into an ERROR finding attributed to the check, rather than letting one
   failure abort the whole scan. Note this is the *opposite* of the rule inside
   a check: a check must never swallow an error into a false COMPLIANT, but the
   runner *must* catch, so one broken check can't make every other control
   silently vanish. Different layer, different responsibility.

2. It has two lives. Imported as a module, `run_all_checks` is the
   transport-agnostic service layer the backend and MCP wrap. Run as a script
   (`python -m detective.runner`), it is the CLI/JSON adapter.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from typing import Any

import boto3

from detective.checks import (
    iam_mfa,
    rds_encryption,
    s3_public_access,
    security_groups,
    tag_compliance,
)
from detective.checks.base import Finding, Severity, Status, account_id_of

# The registry. Every check module exposes `CHECK_ID` and `run(session)`.
# Adding a check is one line here.
CHECKS = [
    s3_public_access,
    iam_mfa,
    security_groups,
    rds_encryption,
    tag_compliance,
]


def run_all_checks(session: boto3.Session) -> list[Finding]:
    """Run every registered check against the session and combine the findings."""
    account = account_id_of(session)
    findings: list[Finding] = []
    for check in CHECKS:
        try:
            findings.extend(check.run(session))
        except Exception as exc:
            # Orchestration-level catch: one check's crash must not abort the
            # scan or silently drop that control. Surface it as an ERROR finding.
            findings.append(_check_failed(check.CHECK_ID, account, exc))
    return findings


def _check_failed(check_id: str, account: str, exc: Exception) -> Finding:
    return Finding(
        check_id=check_id,
        resource_id=f"check:{check_id}",
        resource_arn="",
        resource_type="Detective::Check",
        region="global",
        account_id=account,
        status=Status.ERROR,
        severity=Severity.MEDIUM,
        title=f"Check '{check_id}' failed to run",
        detail=f"{type(exc).__name__}: {exc}"[:500],
        remediation="Investigate the check; results for this control are unavailable.",
        evidence={"error_type": type(exc).__name__},
    )


def summarize(findings: list[Finding]) -> dict[str, Any]:
    """Roll findings up into counts + a compliance score for the dashboard/API."""
    by_status = Counter(f.status for f in findings)
    non_compliant = [f for f in findings if f.status == Status.NON_COMPLIANT]
    by_severity = Counter(f.severity for f in non_compliant)

    # Score = share of evaluable resources that are compliant. ERROR resources
    # are excluded from the denominator: we couldn't judge them, so counting them
    # as pass or fail would both be dishonest.
    evaluable = by_status[Status.COMPLIANT] + by_status[Status.NON_COMPLIANT]
    score = round(by_status[Status.COMPLIANT] / evaluable * 100, 1) if evaluable else None

    return {
        "total_findings": len(findings),
        "by_status": {s.value: by_status[s] for s in Status},
        "non_compliant_by_severity": {s.value: by_severity[s] for s in Severity},
        "compliance_score_pct": score,
    }


def _build_session(profile: str | None, assume_role: str | None, region: str) -> boto3.Session:
    base = boto3.Session(profile_name=profile) if profile else boto3.Session()
    if not assume_role:
        return base
    creds = base.client("sts").assume_role(RoleArn=assume_role, RoleSessionName="detective-runner")[
        "Credentials"
    ]
    return boto3.Session(
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"],
        region_name=region,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run detective compliance checks.")
    parser.add_argument("--profile", help="AWS profile to use for the base session")
    parser.add_argument(
        "--assume-role",
        help="Role ARN to assume (e.g. OrganizationAccountAccessRole in a member account)",
    )
    parser.add_argument("--region", default="us-east-1")
    args = parser.parse_args(argv)

    session = _build_session(args.profile, args.assume_role, args.region)
    findings = run_all_checks(session)
    report = {
        "summary": summarize(findings),
        "findings": [f.to_dict() for f in findings],
    }
    json.dump(report, sys.stdout, indent=2, default=str)
    sys.stdout.write("\n")
    # Non-zero exit when anything is non-compliant — lets this gate a pipeline.
    return 1 if report["summary"]["by_status"]["NON_COMPLIANT"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
