# Corrective Layer — gated remediation of detective findings

Closes the loop: the detective layer emits a `Finding`, this layer matches it by
`check_id` and either **auto-remediates** it (via an SSM Automation runbook) or
**flags a human** — always dry-run first, real mutation only on `apply=True`.

See the [`compliance-check-pattern`](../.claude/skills/compliance-check-pattern)
skill for the runbook rules (idempotent, scoped role, guarded, traceable,
reversible) and [`corrective/base.py`](base.py) for the `Action`/`Outcome` model.

## Design in one line

Every remediation is a **transport-agnostic gated pure function** — the same
shape as a detective check — so the FastAPI backend and the MCP
`trigger_remediation` tool both wrap the one `remediate()` dispatcher and inherit
its safety gate. The `Action` a `check_id` is *allowed* to take is fixed
server-side in [`registry.py`](registry.py); a caller can never request an unsafe
action.

## Coverage — 2 auto-fix, 3 notify

Only findings that can be *safely and reversibly* fixed are auto-remediated. The
rest are flagged, honestly, rather than faked.

| `check_id` | Action | How |
|---|---|---|
| `s3-public-access` | AUTO_REMEDIATE ✅ | SSM runbook re-enables Block Public Access (idempotent, monotonic-secure) |
| `security-groups` | AUTO_REMEDIATE ✅ | SSM runbook (executeScript) revokes only the world-open ingress on sensitive ports — guarded + surgical |
| `rds-encryption` | NOTIFY | Encryption at rest can't be toggled on a live instance — flag a human |
| `iam-mfa` | NOTIFY | Can't enroll another principal's MFA device — flag a human |
| `tag-compliance` | NOTIFY | The missing tag *values* can't be inferred — flag a human |

## Layout

```
corrective/
  base.py                       # Action / Outcome / RemediationResult + the gate contract
  registry.py                   # check_id -> (Action, handler) — the closed allowlist
  remediator.py                 # remediate(): the gated dispatcher (guards ERROR/COMPLIANT/unknown)
  remediations/
    notify.py                   # the 3 notify-and-track checks
    s3_public_access.py         # starts the S3 SSM runbook on apply
    security_groups.py          # starts the SG SSM runbook on apply
  runbooks/
    remediate-s3-public-access.yaml   # SSM doc: re-enable BPA (executeAwsApi)
    remediate-security-groups.yaml    # SSM doc: revoke world-open ingress (executeScript, guarded)
  tests/                        # offline, Stubber-based

infra/corrective/               # Terraform: registers the runbook + a least-privilege role
```

## Status

- **`s3-public-access`: DONE and validated live** — runbook + scoped role deployed
  to the member account; a deliberately-public test bucket was flagged by the
  detective check, dry-run left it untouched, and `apply=True` drove the runbook
  to `Success` and restored all four BPA flags.
- **`security-groups`: DONE and validated live** — a test group with world-open
  (`0.0.0.0/0`) *and* legitimate (`10.0.0.0/8`) ingress on port 22 was flagged;
  `apply=True` drove the runbook to `Success`, revoking only the world-open range
  and leaving the internal CIDR intact (surgical), then cleaned up.
- **notify handlers (`rds-encryption`, `iam-mfa`, `tag-compliance`): DONE.**

The corrective layer is now feature-complete: both auto-remediations and all
three notify handlers are built, tested, and (for the auto-fixes) validated live.
