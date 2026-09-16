# Cloud Compliance Guardian — Final Report

> Living document — sections are filled in as the write-up progresses.

## Preventive layer

### Why the four required tags

Every governed resource must carry four tags at creation, each preventing a specific
failure:

- **`owner`** (email/team) — *accountability*: who gets paged when a resource is
  compromised or misbehaving; no owner means orphaned infrastructure nobody will touch.
- **`environment`** (`prod`|`staging`|`dev`|`sandbox`) — *blast radius & policy*: backup,
  change-control, and security rules differ per environment, and automation (including
  remediation) must tell prod from a sandbox before it acts.
- **`cost-center`** (billing code) — *cost attribution*: untagged resources are
  untraceable spend.
- **`data-classification`** (`public`|`internal`|`confidential`|`restricted`) —
  *compliance & security controls*: encryption, access, and retention requirements follow
  from the classification; an unclassified store could hold PII with none of the required
  controls.

These four are the contract the whole system relies on — the detective layer scans for
them, the dashboard groups by them, and cost reporting attributes spend through them.
Enforcing them **on create** (via the SCP) means the tag debt is never created in the
first place, rather than chasing untagged resources after the fact.

## Detective layer

### AWS Config managed rules

`required-tags` is the AWS-managed `REQUIRED_TAGS` Config rule, fed your four keys
(`owner`, `environment`, `cost-center`, `data-classification`) with no values, and it
continuously flags any supported resource missing *any* of the four as `NON_COMPLIANT`
— a presence check that complements the create-time SCP.

### Boto3 checks

A set of transport-agnostic, paginated, multi-region Boto3 check functions (one per
rule — S3 public access, open security groups, IAM/root MFA, RDS encryption, tag
compliance) that scan the live account on demand and return uniform `Finding` objects,
failing toward flagging (`ERROR`, never a silent pass) when a resource can't be
evaluated.
