"""Check: rds-encryption — flag RDS DB instances not encrypted at rest.

Regional, like security groups, so we loop enabled regions. Encryption at rest
is set only at creation time (`StorageEncrypted`); an unencrypted instance can't
be encrypted in place — it must be snapshotted and restored encrypted, which is
why we flag it rather than assuming it'll be fixed cheaply.
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

CHECK_ID = "rds-encryption"


def run(session: boto3.Session) -> list[Finding]:
    account = account_id_of(session)
    findings: list[Finding] = []
    for region in enabled_regions(session):
        rds = session.client("rds", region_name=region, config=BOTO_CONFIG)
        for page in rds.get_paginator("describe_db_instances").paginate():
            for db in page["DBInstances"]:
                findings.append(_evaluate_db(account, region, db))
    return findings


def _evaluate_db(account: str, region: str, db: dict) -> Finding:
    ident = db["DBInstanceIdentifier"]
    base = {
        "check_id": CHECK_ID,
        "resource_id": ident,
        "resource_arn": db.get("DBInstanceArn", f"arn:aws:rds:{region}:{account}:db:{ident}"),
        "resource_type": "AWS::RDS::DBInstance",
        "region": region,
        "account_id": account,
    }
    if db.get("StorageEncrypted", False):
        return Finding(
            **base,
            status=Status.COMPLIANT,
            severity=Severity.LOW,
            title="RDS instance is encrypted at rest",
            detail=f"DB instance '{ident}' has StorageEncrypted enabled.",
            remediation="None — compliant.",
            evidence={"storage_encrypted": True},
        )
    return Finding(
        **base,
        status=Status.NON_COMPLIANT,
        severity=Severity.HIGH,
        title="RDS instance is not encrypted at rest",
        detail=f"DB instance '{ident}' has StorageEncrypted disabled.",
        remediation="Snapshot the instance and restore it with encryption enabled.",
        evidence={"storage_encrypted": False},
    )
