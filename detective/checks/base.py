"""Shared foundation for every detective check.

The contract: a check is a **pure function** with the signature

    def run(session: boto3.Session) -> list[Finding]

It takes an already-authenticated Boto3 session, evaluates one compliance
concern, and returns findings. It does not print, does not touch HTTP, and holds
no global state. That is what lets the *same* function be called by the runner,
the FastAPI backend, and the MCP server without change — the transport-agnostic
service layer.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import boto3
from botocore.config import Config

# One shared botocore config, reused by every client. Adaptive retries back off
# automatically under throttling — essential when a check paginates over a large
# account and AWS starts rate-limiting.
BOTO_CONFIG = Config(retries={"max_attempts": 10, "mode": "adaptive"})


class Status(StrEnum):
    """A check's verdict for one resource. ERROR is deliberately NOT a pass."""

    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    ERROR = "ERROR"  # could not evaluate (e.g. AccessDenied) — never treat as clean


class Severity(StrEnum):
    """Blast radius of the finding, not how annoying the fix is."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass(frozen=True)
class Finding:
    """The one record shape the whole system speaks.

    Emitted by detective checks, served by the backend, rendered by the
    dashboard, and matched to a runbook by the corrective layer via `check_id`.
    Frozen so a finding can't be mutated after a check hands it back.
    """

    check_id: str  # stable, kebab-case; maps 1:1 to a corrective runbook
    resource_id: str  # bucket name, instance id, role name, ...
    resource_arn: str  # full ARN; the dashboard links on this
    resource_type: str  # CloudFormation-style, e.g. "AWS::S3::Bucket"
    region: str  # "global" for IAM/S3-style global services
    account_id: str
    status: Status
    severity: Severity
    title: str  # short, human-readable
    detail: str  # what specifically was wrong, including the observed value
    remediation: str  # the fix, in one sentence
    # Allowlisted, size-bounded proof of the verdict — NEVER the raw API response
    # (those carry secrets/PII and this dict flows to the dashboard).
    evidence: dict[str, Any] = field(default_factory=dict)
    checked_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable form for the runner / API boundary."""
        d = asdict(self)
        d["status"] = self.status.value
        d["severity"] = self.severity.value
        d["checked_at"] = self.checked_at.isoformat()
        return d


def account_id_of(session: boto3.Session) -> str:
    """Resolve the account id the session is operating in (one STS call)."""
    return session.client("sts", config=BOTO_CONFIG).get_caller_identity()["Account"]


def enabled_regions(session: boto3.Session) -> list[str]:
    """Regions enabled for this account. Regional checks must loop over these —
    a security group open to the world in eu-west-1 is just as exposed as one in
    us-east-1, and scanning a single region would silently miss it."""
    ec2 = session.client("ec2", region_name="us-east-1", config=BOTO_CONFIG)
    return [r["RegionName"] for r in ec2.describe_regions()["Regions"]]
