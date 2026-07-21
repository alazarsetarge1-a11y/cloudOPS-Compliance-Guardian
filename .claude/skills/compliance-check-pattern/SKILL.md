---
name: compliance-check-pattern
description: The house pattern for writing Boto3 compliance checks and SSM Automation remediation runbooks. Use when working in detective/ or corrective/, when adding or reviewing an AWS compliance check (S3 public access, IAM MFA, open security groups, RDS encryption, tag compliance), when defining the finding data shape, or when writing a runbook that mutates AWS resources.
---

# Detective checks and corrective runbooks

## The finding schema — one shape, three consumers

Every detective check emits the same record. The backend serves it, the frontend
renders it, and the corrective layer keys off `check_id` to pick a runbook. Keep
this stable; changing it means touching all three layers.

```python
@dataclass
class Finding:
    check_id: str          # "s3-public-access" — stable, kebab-case, maps 1:1 to a runbook
    resource_id: str       # bucket name, instance id, role name
    resource_arn: str      # full ARN; the frontend links on this
    resource_type: str     # "AWS::S3::Bucket" — CloudFormation type notation
    region: str
    account_id: str
    status: str            # COMPLIANT | NON_COMPLIANT | ERROR  (ERROR is not a pass)
    severity: str          # CRITICAL | HIGH | MEDIUM | LOW
    title: str             # short, human-readable
    detail: str            # what specifically was wrong, with the observed value
    remediation: str       # what fixes it, in one sentence
    evidence: dict         # raw API response fragment that justified the verdict
    checked_at: datetime    # UTC, timezone-aware
```

`evidence` matters more than it looks. In a compliance context, a finding
without the underlying API response backing it is an assertion, not evidence.
It is also what lets the dashboard show *why* something was flagged.

## Three rules that separate a real check from a script

### 1. Paginate, always

```python
# WRONG — silently reports only the first page. Resources 101+ appear compliant.
buckets = s3.list_buckets()["Buckets"]

# RIGHT
paginator = iam.get_paginator("list_users")
for page in paginator.paginate():
    for user in page["Users"]:
        ...
```

This is the highest-value bug class in compliance tooling because it fails
*quietly* and in the safe-looking direction. An account with 40 users passes
your test; the account with 400 that you actually care about does not get fully
scanned. Use a paginator whenever one exists — check
`client.can_paginate("operation_name")` if unsure.

### 2. `ERROR` is not `COMPLIANT`

```python
# WRONG — an AccessDenied becomes a clean bill of health.
try:
    cfg = s3.get_public_access_block(Bucket=name)
except ClientError:
    return Finding(status="COMPLIANT", ...)

# RIGHT — distinguish "genuinely absent" from "could not evaluate".
try:
    cfg = s3.get_public_access_block(Bucket=name)
except ClientError as e:
    code = e.response["Error"]["Code"]
    if code == "NoSuchPublicAccessBlockConfiguration":
        # Absence IS the finding: no block config means public access is possible.
        return Finding(status="NON_COMPLIANT", detail="No public access block configured", ...)
    if code in ("AccessDenied", "AccessDeniedException"):
        return Finding(status="ERROR", detail=f"Cannot evaluate: {code}", ...)
    raise
```

Never write a bare `except Exception: pass` in a check. A compliance tool that
reports "all clear" because it lacked permission to look is worse than no tool —
it manufactures false confidence.

### 3. One client, reused

Construct Boto3 clients once at module or class level, not inside the per-
resource loop. Client construction does credential resolution and endpoint
discovery; doing it per resource is slow and can trigger throttling. Add a
retry config for large accounts:

```python
from botocore.config import Config

BOTO_CFG = Config(retries={"max_attempts": 10, "mode": "adaptive"})
s3 = boto3.client("s3", config=BOTO_CFG)
```

## Credentials

Never in code, never in a config file, never in a constructor argument.
Credentials come from the environment: your local AWS profile when developing,
the ECS task role in production. If you find yourself typing `aws_access_key_id=`
anywhere, stop — that is the bug gitleaks exists to catch.

## Severity — pick it deliberately

Map to blast radius, not to how annoying the fix is.

- **CRITICAL** — data exposed to the internet right now, or credentials
  compromised. Public S3 bucket with objects, root account without MFA.
- **HIGH** — direct path to compromise. Security group open to 0.0.0.0/0 on
  22/3389, IAM user with `AdministratorAccess` and no MFA.
- **MEDIUM** — meaningful weakening of defense in depth. Unencrypted RDS at
  rest, missing CloudTrail in a region.
- **LOW** — hygiene and governance. Missing required tags, unused credentials.

Be able to defend every rating. "Why is that HIGH and not CRITICAL?" is a
realistic interview question.

## Corrective runbooks

Each runbook maps to exactly one `check_id`. Rules:

- **Idempotent.** Running it against an already-remediated resource must succeed
  and change nothing. Automation retries; non-idempotent runbooks corrupt state.
- **Scoped IAM role.** The automation role gets the minimum action set on the
  minimum resources, conditioned by tag where possible. Never a mutating action
  on `Resource: "*"`.
- **Guarded.** Before mutating, re-verify the resource is still non-compliant.
  The finding may be stale by the time the runbook runs.
- **Traceable.** Emit what was changed, on what resource, at what time, and
  which finding triggered it. The dashboard's remediation timeline is only as
  honest as this record.
- **Reversible where possible.** Prefer restricting a security group rule over
  deleting the group. Prefer enabling a public access block over deleting a
  bucket. Never write a runbook that deletes data.

## Config rules vs. Boto3 checks — know why both exist

AWS Config gives continuous, event-driven evaluation with built-in history and
no compute to run — but you are limited to managed rules or Lambda-backed custom
rules, and it bills per evaluation. Boto3 checks give full control and run
anywhere, but they are point-in-time and you own the scheduling and compute.

This project uses **Config for the baseline rules that have good managed
equivalents**, and **Boto3 for the cross-cutting checks Config does not express
well** (e.g. correlating IAM role tags with policy scope). Be ready to explain
that split — it is a design decision, not an accident.
