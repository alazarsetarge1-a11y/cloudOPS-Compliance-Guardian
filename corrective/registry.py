"""The single source of truth for what each finding is *allowed* to do.

``Action`` is fixed here, at design time. It is NOT a call-time parameter — a
caller (a FastAPI request body, or an LLM driving the MCP tool) can never ask for
``AUTO_REMEDIATE`` on a finding we only vetted for ``NOTIFY``. The safe set is
server-side and closed; unsafe remediations are simply not expressible.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from corrective.base import Action, RemediationResult
from corrective.remediations.notify import notify
from corrective.remediations.s3_public_access import remediate_s3_public_access
from corrective.remediations.security_groups import remediate_security_groups

# A handler is a transport-agnostic pure function; apply is keyword-only so it
# can never be passed True positionally by accident.
Handler = Callable[..., RemediationResult]


@dataclass(frozen=True)
class RemediationSpec:
    """What a check_id may do, and the function that does it."""

    action: Action
    handler: Handler


REGISTRY: dict[str, RemediationSpec] = {
    # --- Notify-and-track: cannot be safely auto-fixed (see notify.py) ---
    "rds-encryption": RemediationSpec(Action.NOTIFY, notify),
    "iam-mfa": RemediationSpec(Action.NOTIFY, notify),
    "tag-compliance": RemediationSpec(Action.NOTIFY, notify),
    # --- Auto-remediable: SSM-backed handlers ---
    "s3-public-access": RemediationSpec(Action.AUTO_REMEDIATE, remediate_s3_public_access),
    "security-groups": RemediationSpec(Action.AUTO_REMEDIATE, remediate_security_groups),
}
