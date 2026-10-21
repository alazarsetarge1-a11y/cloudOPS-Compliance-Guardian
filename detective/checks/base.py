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

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
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

# Guards boto3 client CREATION. A boto3.Session is not thread-safe for *building*
# clients — credential resolution and the session's internal component cache can
# race under concurrent creation — but a client, once built, is safe to call from
# many threads. The scan fans checks (and regions within a check) out across
# threads on one shared session, so every client is created through `make_client`,
# serialized by this lock. Creation is a fast local operation (no network), so
# holding the lock costs almost nothing while the AWS calls still run in parallel.
_CLIENT_LOCK = threading.Lock()

# Upper bound on concurrent per-region calls inside a single regional check. The
# fan-out is I/O-bound (each worker just blocks on a socket), so more threads than
# regions buys nothing; this only caps thread/connection churn on big accounts.
_REGION_FANOUT = 16


def make_client(session: boto3.Session, service: str, **kwargs: Any) -> Any:
    """Build a boto3 client for `service`, serialized against concurrent creation.

    Always applies BOTO_CONFIG. This is the ONE place clients are created, so the
    Session-not-thread-safe-for-creation hazard is handled in exactly one spot
    rather than being re-reasoned about in every check. Every check builds its
    clients through here.
    """
    with _CLIENT_LOCK:
        return session.client(service, config=BOTO_CONFIG, **kwargs)


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
    return make_client(session, "sts").get_caller_identity()["Account"]


def enabled_regions(session: boto3.Session) -> list[str]:
    """Regions enabled for this account. Regional checks must cover all of these —
    a security group open to the world in eu-west-1 is just as exposed as one in
    us-east-1, and scanning a single region would silently miss it."""
    ec2 = make_client(session, "ec2", region_name="us-east-1")
    return [r["RegionName"] for r in ec2.describe_regions()["Regions"]]


def scan_regions(
    session: boto3.Session,
    service: str,
    scan_region: Callable[[str, Any], list[Finding]],
) -> list[Finding]:
    """Run `scan_region(region, client)` for every enabled region, concurrently.

    Regional checks are network-bound: ~N sequential `describe_*` round-trips,
    one per region, with the CPU idle waiting on each socket. A thread pool
    overlaps those waits — a blocking boto3 call releases the GIL — turning N
    serial round-trips into roughly one round-trip of wall time.

    Clients are built up front via `make_client` (lock-guarded); the pool only
    ever *calls* already-built clients, which is thread-safe. If a region's scan
    raises, the exception propagates out of here, the check fails, and the runner
    records one ERROR finding for the whole check — the same semantics as the old
    serial loop, just faster.
    """
    regions = enabled_regions(session)
    clients = {region: make_client(session, service, region_name=region) for region in regions}

    findings: list[Finding] = []
    with ThreadPoolExecutor(max_workers=min(_REGION_FANOUT, len(regions) or 1)) as pool:
        # map() preserves submission order and re-raises a worker's exception when
        # its result is consumed, so one failing region aborts the check as before.
        for region_findings in pool.map(lambda item: scan_region(*item), clients.items()):
            findings.extend(region_findings)
    return findings
