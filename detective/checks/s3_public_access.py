"""Check: s3-public-access — flag S3 buckets not fully protected from public exposure.

A bucket's **S3 Block Public Access (BPA)** configuration is the control that
stops it from being made public via an ACL or a bucket policy. It has four flags;
all four must be on for the bucket to be fully protected. A bucket with no BPA
config at all, or with any flag disabled, *can* be exposed publicly — so we flag
it. The absence of a BPA config is itself the finding.
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

# All four must be True for a bucket to be fully locked against public access.
_BPA_FLAGS = (
    "BlockPublicAcls",
    "IgnorePublicAcls",
    "BlockPublicPolicy",
    "RestrictPublicBuckets",
)


def run(session: boto3.Session) -> list[Finding]:
    """Evaluate every S3 bucket in the account for public-access protection."""
    s3 = session.client("s3", config=BOTO_CONFIG)  # one client, reused for all buckets
    account = account_id_of(session)
    return [_evaluate_bucket(s3, account, name) for name in _all_bucket_names(s3)]


def _all_bucket_names(s3) -> list[str]:
    # list_buckets gained pagination for accounts with many buckets. Use the
    # paginator when it exists so we never silently evaluate only the first page.
    if s3.can_paginate("list_buckets"):
        names: list[str] = []
        for page in s3.get_paginator("list_buckets").paginate():
            names.extend(b["Name"] for b in page.get("Buckets", []))
        return names
    return [b["Name"] for b in s3.list_buckets().get("Buckets", [])]


def _evaluate_bucket(s3, account: str, name: str) -> Finding:
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
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "NoSuchPublicAccessBlockConfiguration":
            # No BPA at all → public access is possible. Absence IS the finding.
            return Finding(
                **base,
                status=Status.NON_COMPLIANT,
                severity=Severity.HIGH,
                title="Bucket has no Block Public Access configuration",
                detail="No Block Public Access is set, so this bucket can be made "
                "public via a bucket ACL or bucket policy.",
                remediation="Enable all four S3 Block Public Access settings on the "
                "bucket (or account-wide).",
                evidence={"block_public_access": None},
            )
        if code in ("AccessDenied", "AccessDeniedException"):
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
        raise  # unknown error: surface it, don't swallow it into a false pass

    disabled = [flag for flag in _BPA_FLAGS if not cfg.get(flag, False)]
    if disabled:
        return Finding(
            **base,
            status=Status.NON_COMPLIANT,
            severity=Severity.HIGH,
            title="Bucket is not fully protected by Block Public Access",
            detail=f"These Block Public Access flags are disabled: {', '.join(disabled)}.",
            remediation="Enable all four Block Public Access flags on the bucket.",
            evidence={flag: cfg.get(flag, False) for flag in _BPA_FLAGS},
        )

    return Finding(
        **base,
        status=Status.COMPLIANT,
        severity=Severity.LOW,
        title="Bucket is protected by Block Public Access",
        detail="All four Block Public Access flags are enabled.",
        remediation="None — bucket is compliant.",
        evidence=dict.fromkeys(_BPA_FLAGS, True),
    )
