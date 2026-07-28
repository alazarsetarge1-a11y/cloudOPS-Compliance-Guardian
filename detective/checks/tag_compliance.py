"""Check: tag-compliance — flag resources missing the four required tags.

This is the detective counterpart to the preventive SCP. The SCP blocks *new*
untagged resources, but it can't help with resources that already existed before
it, that live in accounts it isn't attached to, or of types it doesn't gate.
This check catches those — the same four tags, evaluated continuously after the
fact. It's why "preventive + detective" beats either alone.

Uses the Resource Groups Tagging API (`get_resources`), which returns taggable
resources across services in one paginated call. It is regional, so we loop.
"""

from __future__ import annotations

import boto3

from detective.checks.base import (
    BOTO_CONFIG,
    Finding,
    Severity,
    Status,
    account_id_of,
    enabled_regions,
)

CHECK_ID = "tag-compliance"
# Must match the SCP's required tags exactly — this is the same contract, enforced
# preventively there and detectively here.
REQUIRED_TAGS = ("owner", "environment", "cost-center", "data-classification")


def run(session: boto3.Session) -> list[Finding]:
    account = account_id_of(session)
    findings: list[Finding] = []
    for region in enabled_regions(session):
        tagging = session.client("resourcegroupstaggingapi", region_name=region, config=BOTO_CONFIG)
        for page in tagging.get_paginator("get_resources").paginate():
            for resource in page["ResourceTagMappingList"]:
                findings.append(_evaluate_resource(account, region, resource))
    return findings


def _evaluate_resource(account: str, region: str, resource: dict) -> Finding:
    arn = resource["ResourceARN"]
    present = {t["Key"] for t in resource.get("Tags", [])}
    missing = [key for key in REQUIRED_TAGS if key not in present]
    base = {
        "check_id": CHECK_ID,
        "resource_id": arn.rsplit(":", 1)[-1].rsplit("/", 1)[-1] or arn,
        "resource_arn": arn,
        "resource_type": "AWS::TaggedResource",
        "region": region,
        "account_id": account,
    }
    if missing:
        return Finding(
            **base,
            status=Status.NON_COMPLIANT,
            severity=Severity.MEDIUM,
            title="Resource is missing required tags",
            detail=f"Missing required tag(s): {', '.join(missing)}.",
            remediation="Add the missing tags; untagged resources are untraceable for "
            "ownership, cost, and data classification.",
            evidence={"missing_tags": missing},
        )
    return Finding(
        **base,
        status=Status.COMPLIANT,
        severity=Severity.LOW,
        title="Resource has all required tags",
        detail="All four required tags are present.",
        remediation="None — compliant.",
        evidence={"missing_tags": []},
    )
