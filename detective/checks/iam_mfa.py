"""Check: iam-mfa — flag the account root and IAM console users lacking MFA.

New wrinkles vs the S3 check:
- IAM is a GLOBAL service — no region loop.
- The root user is NOT returned by list_users; its MFA state comes from the
  account summary. Root without MFA is the worst case (root is unrestricted and
  can't even be capped by an SCP), so it's CRITICAL.
- Only *console* users (those with a login profile) are in scope for MFA. A user
  with only access keys signs in programmatically, not via the console.
"""

from __future__ import annotations

import boto3
from botocore.exceptions import ClientError

from detective.checks.base import BOTO_CONFIG, Finding, Severity, Status, account_id_of

CHECK_ID = "iam-mfa"


def run(session: boto3.Session) -> list[Finding]:
    iam = session.client("iam", config=BOTO_CONFIG)
    account = account_id_of(session)
    findings = [_evaluate_root(iam, account)]
    for page in iam.get_paginator("list_users").paginate():
        for user in page["Users"]:
            finding = _evaluate_user(iam, account, user)
            if finding is not None:  # None = not a console user, out of scope
                findings.append(finding)
    return findings


def _evaluate_root(iam, account: str) -> Finding:
    mfa_on = iam.get_account_summary()["SummaryMap"].get("AccountMFAEnabled", 0) == 1
    base = {
        "check_id": CHECK_ID,
        "resource_id": "<root-account>",
        "resource_arn": f"arn:aws:iam::{account}:root",
        "resource_type": "AWS::IAM::RootUser",
        "region": "global",
        "account_id": account,
    }
    if mfa_on:
        return Finding(
            **base,
            status=Status.COMPLIANT,
            severity=Severity.LOW,
            title="Root user has MFA enabled",
            detail="The account root user has an MFA device.",
            remediation="None — compliant.",
            evidence={"account_mfa_enabled": True},
        )
    return Finding(
        **base,
        status=Status.NON_COMPLIANT,
        severity=Severity.CRITICAL,
        title="Root user has no MFA",
        detail="The account root user has no MFA device. Root is unrestricted and "
        "cannot be limited by IAM policies or SCPs.",
        remediation="Enable MFA on the root user immediately.",
        evidence={"account_mfa_enabled": False},
    )


def _evaluate_user(iam, account: str, user: dict) -> Finding | None:
    name = user["UserName"]
    base = {
        "check_id": CHECK_ID,
        "resource_id": name,
        "resource_arn": user["Arn"],
        "resource_type": "AWS::IAM::User",
        "region": "global",
        "account_id": account,
    }

    # Console access? get_login_profile raises NoSuchEntity when there's none.
    try:
        iam.get_login_profile(UserName=name)
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "NoSuchEntity":
            return None  # programmatic-only user — MFA not in scope for this check
        if code in ("AccessDenied", "AccessDeniedException"):
            return Finding(
                **base,
                status=Status.ERROR,
                severity=Severity.MEDIUM,
                title="Could not evaluate user MFA",
                detail=f"Access denied checking console access ({code}).",
                remediation="Grant iam:GetLoginProfile / iam:ListMFADevices to the scanning role.",
                evidence={"error": code},
            )
        raise

    # Paginate for consistency with the "always paginate" rule (a user can't
    # actually exceed one page of MFA devices, but we don't special-case it).
    has_mfa = any(
        page["MFADevices"] for page in iam.get_paginator("list_mfa_devices").paginate(UserName=name)
    )
    if has_mfa:
        return Finding(
            **base,
            status=Status.COMPLIANT,
            severity=Severity.LOW,
            title="Console user has MFA",
            detail=f"IAM user '{name}' has console access and an MFA device.",
            remediation="None — compliant.",
            evidence={"console_access": True, "mfa_devices": 1},
        )
    return Finding(
        **base,
        status=Status.NON_COMPLIANT,
        severity=Severity.HIGH,
        title="Console user without MFA",
        detail=f"IAM user '{name}' can sign in to the console but has no MFA device.",
        remediation="Assign an MFA device and enforce MFA for this user.",
        evidence={"console_access": True, "mfa_devices": 0},
    )
