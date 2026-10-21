"""Check: security-groups — flag security groups open to the internet on sensitive ports.

New wrinkle: EC2 security groups are REGIONAL, so we loop over every enabled
region — an SG open to 0.0.0.0/0 on SSH in eu-west-1 is just as dangerous as one
in us-east-1. The evaluation itself (`_world_open_sensitive`) is a pure function
over the SG dict, so it's unit-tested with plain literals — no AWS.
"""

from __future__ import annotations

from typing import Any

import boto3

from detective.checks.base import (
    Finding,
    Severity,
    Status,
    account_id_of,
    scan_regions,
)

CHECK_ID = "security-groups"
SENSITIVE_PORTS = (22, 3389)  # SSH, RDP — the classic "never open to the world" ports
_OPEN_V4 = "0.0.0.0/0"
_OPEN_V6 = "::/0"


def run(session: boto3.Session) -> list[Finding]:
    account = account_id_of(session)

    def scan_region(region: str, ec2: Any) -> list[Finding]:
        found: list[Finding] = []
        for page in ec2.get_paginator("describe_security_groups").paginate():
            for sg in page["SecurityGroups"]:
                found.append(_evaluate_sg(account, region, sg))
        return found

    # Regional: fan the per-region describe calls out across threads (see
    # base.scan_regions) instead of walking ~17 regions one blocking call at a time.
    return scan_regions(session, "ec2", scan_region)


def _world_open_sensitive(sg: dict) -> list[str]:
    """Return human-readable descriptions of world-open sensitive exposures, if any."""
    exposures: list[str] = []
    for perm in sg.get("IpPermissions", []):
        world = any(r.get("CidrIp") == _OPEN_V4 for r in perm.get("IpRanges", [])) or any(
            r.get("CidrIpv6") == _OPEN_V6 for r in perm.get("Ipv6Ranges", [])
        )
        if not world:
            continue
        if perm.get("IpProtocol") == "-1":  # -1 = all protocols/all ports
            exposures.append("ALL traffic")
            continue
        from_port, to_port = perm.get("FromPort"), perm.get("ToPort")
        if from_port is None or to_port is None:
            continue
        exposures.extend(
            f"{perm['IpProtocol']}/{port}"
            for port in SENSITIVE_PORTS
            if from_port <= port <= to_port
        )
    return exposures


def _evaluate_sg(account: str, region: str, sg: dict) -> Finding:
    gid = sg["GroupId"]
    base = {
        "check_id": CHECK_ID,
        "resource_id": gid,
        "resource_arn": f"arn:aws:ec2:{region}:{account}:security-group/{gid}",
        "resource_type": "AWS::EC2::SecurityGroup",
        "region": region,
        "account_id": account,
    }
    exposures = _world_open_sensitive(sg)
    if exposures:
        return Finding(
            **base,
            status=Status.NON_COMPLIANT,
            severity=Severity.HIGH,
            title="Security group open to the internet on a sensitive port",
            detail=f"Ingress from {_OPEN_V4}/{_OPEN_V6} allows: {', '.join(exposures)}.",
            remediation="Restrict the ingress rule to known CIDRs or a bastion/VPN.",
            evidence={"world_open": exposures},
        )
    return Finding(
        **base,
        status=Status.COMPLIANT,
        severity=Severity.LOW,
        title="Security group has no world-open sensitive ports",
        detail="No ingress from the internet on SSH/RDP or all-traffic.",
        remediation="None — compliant.",
        evidence={"world_open": []},
    )
