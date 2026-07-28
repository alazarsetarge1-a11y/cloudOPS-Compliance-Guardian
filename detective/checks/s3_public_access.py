"""Check: s3-public-access — flag S3 buckets not fully protected from public exposure.

S3 Block Public Access (BPA) has four flags; all four must be on for a bucket to
be fully protected. Crucially, S3 applies the **most restrictive of account-level
and bucket-level** BPA — so a bucket with no bucket-level config can still be
fully protected by an account-wide block. This check reads BOTH and evaluates the
*effective* state, so it doesn't false-positive a bucket that account-level BPA
already protects. Absence of protection at both levels is the finding.
"""

from __future__ import annotations

import boto3
from botocore.exceptions import ClientError

from detective.checks.base import (
    BOTO_CONFIG,
    Finding,
    Severity,
    Status,
    account_id_of,
)

CHECK_ID = "s3-public-access"

# All four must be effectively True for a bucket to be fully locked down.
_BPA_FLAGS = (
    "BlockPublicAcls",
    "IgnorePublicAcls",
    "BlockPublicPolicy",
    "RestrictPublicBuckets",
)


def run(session: boto3.Session) -> list[Finding]:
    """Evaluate every S3 bucket for effective (account + bucket) public-access protection."""
    s3 = session.client("s3", config=BOTO_CONFIG)  # one client, reused for all buckets
    account = account_id_of(session)
    account_bpa = _account_level_bpa(session, account)  # read once, applies to every bucket
    return [_evaluate_bucket(s3, account, account_bpa, name) for name in _all_bucket_names(s3)]


def _all_bucket_names(s3) -> list[str]:
    # list_buckets gained pagination for accounts with many buckets. Use the
    # paginator when it exists so we never silently evaluate only the first page.
    if s3.can_paginate("list_buckets"):
        names: list[str] = []
        for page in s3.get_paginator("list_buckets").paginate():
            names.extend(b["Name"] for b in page.get("Buckets", []))
        return names
    return [b["Name"] for b in s3.list_buckets().get("Buckets", [])]


def _account_level_bpa(session: boto3.Session, account: str) -> dict[str, bool]:
    """Account-wide BPA flags (via s3control). Missing config or no read access →
    assume no account-level protection, i.e. evaluate on bucket-level alone
    (fail toward flagging for review, never toward a false pass)."""
    s3control = session.client("s3control", region_name="us-east-1", config=BOTO_CONFIG)
    try:
        cfg = s3control.get_public_access_block(AccountId=account)["PublicAccessBlockConfiguration"]
        return {flag: cfg.get(flag, False) for flag in _BPA_FLAGS}
    except ClientError as e:
        if e.response["Error"]["Code"] in (
            "NoSuchPublicAccessBlockConfiguration",
            "AccessDenied",
            "AccessDeniedException",
        ):
            return dict.fromkeys(_BPA_FLAGS, False)
        raise


def _evaluate_bucket(s3, account: str, account_bpa: dict[str, bool], name: str) -> Finding:
    base = {
        "check_id": CHECK_ID,
        "resource_id": name,
        "resource_arn": f"arn:aws:s3:::{name}",  # S3 bucket ARNs are global — no region/account
        "resource_type": "AWS::S3::Bucket",
        "region": "global",
        "account_id": account,
    }

    try:
        cfg = s3.get_public_access_block(Bucket=name)["PublicAccessBlockConfiguration"]
        bucket_bpa = {flag: cfg.get(flag, False) for flag in _BPA_FLAGS}
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "NoSuchPublicAccessBlockConfiguration":
            bucket_bpa = dict.fromkeys(_BPA_FLAGS, False)  # no bucket-level config
        elif code in ("AccessDenied", "AccessDeniedException"):
            # Could not evaluate — this is ERROR, never a silent COMPLIANT.
            return Finding(
                **base,
                status=Status.ERROR,
                severity=Severity.MEDIUM,
                title="Could not evaluate bucket public access",
                detail=f"Access denied reading the Block Public Access config ({code}).",
                remediation="Grant s3:GetBucketPublicAccessBlock to the scanning role.",
                evidence={"error": code},
            )
        else:
            raise  # unknown error: surface it, don't swallow it into a false pass

    # Effective protection = the most restrictive of account- and bucket-level.
    effective = {flag: account_bpa[flag] or bucket_bpa[flag] for flag in _BPA_FLAGS}
    disabled = [flag for flag in _BPA_FLAGS if not effective[flag]]

    if disabled:
        return Finding(
            **base,
            status=Status.NON_COMPLIANT,
            severity=Severity.HIGH,
            title="Bucket is not fully protected by Block Public Access",
            detail="Effective Block Public Access (account + bucket) leaves these flags "
            f"disabled: {', '.join(disabled)} — the bucket can be exposed publicly.",
            remediation="Enable all four Block Public Access flags at the bucket or account level.",
            evidence={"effective_block_public_access": effective, "disabled": disabled},
        )

    return Finding(
        **base,
        status=Status.COMPLIANT,
        severity=Severity.LOW,
        title="Bucket is protected by Block Public Access",
        detail="All four Block Public Access flags are effectively enabled "
        "(account and/or bucket level).",
        remediation="None — compliant.",
        evidence={"effective_block_public_access": effective},
    )
