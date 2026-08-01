"""Shared foundation for the corrective layer.

The contract mirrors the detective layer's on purpose. A remediation is a
**gated pure function**:

    def remediate(finding: Finding, session: boto3.Session, *, apply: bool = False)
        -> RemediationResult

It takes a Finding (emitted by a detective check) and an authenticated session,
and it returns what it *would* do. It performs a real AWS mutation ONLY when
called with ``apply=True``; the default is a dry run that returns the plan and
touches nothing.

That single ``apply`` flag is the whole safety gate. Because the logic lives in
one pure function, the Step-4 FastAPI backend and the Step-7 MCP
``trigger_remediation`` tool both wrap the *same* function and inherit the gate
for free — neither can accidentally skip it.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from botocore.config import Config

# Same reused, throttling-aware client config the detective layer uses.
BOTO_CONFIG = Config(retries={"max_attempts": 10, "mode": "adaptive"})


class Action(StrEnum):
    """What CAN be done about a class of finding — a fixed property of the
    ``check_id``, decided at design time, not per run.

    Being explicit here is the honest core of the layer: not every violation is
    safely auto-fixable, and pretending otherwise is how a remediation program
    breaks something in production.
    """

    AUTO_REMEDIATE = "AUTO_REMEDIATE"  # a runbook can safely, reversibly fix it
    NOTIFY = "NOTIFY"  # cannot be auto-fixed (or too destructive) — flag a human


class Outcome(StrEnum):
    """What actually happened on THIS call. Distinct from Action: a finding whose
    Action is AUTO_REMEDIATE still yields Outcome PLANNED on a dry run."""

    PLANNED = "PLANNED"  # dry run — this is what an apply=True call would do
    REMEDIATED = "REMEDIATED"  # apply=True — the fix was executed/started
    NOTIFIED = "NOTIFIED"  # apply=True — a human was flagged (no auto-fix)
    SKIPPED = "SKIPPED"  # nothing to do (finding not NON_COMPLIANT)
    FAILED = "FAILED"  # a fix was attempted but the AWS call errored


@dataclass(frozen=True)
class RemediationResult:
    """The one record shape the corrective layer speaks — the mirror of Finding.

    Returned by every remediation whether it ran or only planned, so the caller
    (runner / backend / MCP / dashboard) gets one predictable shape to render
    and to persist as remediation history. Frozen for the same reason Finding is:
    a result is a fact about one call and must not be mutated afterward.
    """

    check_id: str  # the finding's check_id — ties the result back 1:1
    resource_id: str
    action: Action  # what this check_id's remediation is allowed to do
    outcome: Outcome  # what this call actually did
    summary: str  # one human-readable sentence for the dashboard/timeline
    # The concrete API call the runbook would make / made — the auditable plan.
    # e.g. {"api": "s3:PutPublicAccessBlock", "params": {"Bucket": "..."}}
    # or, for an SSM-backed apply, {"execution_id": "..."} once started.
    plan: dict[str, Any] = field(default_factory=dict)
    executed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable form for the runner / API boundary."""
        d = asdict(self)
        d["action"] = self.action.value
        d["outcome"] = self.outcome.value
        d["executed_at"] = self.executed_at.isoformat()
        return d
