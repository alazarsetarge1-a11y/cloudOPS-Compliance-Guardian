---
name: scp-authoring
description: Write, review, or test AWS Organizations Service Control Policies (SCPs) for the preventive layer. Use whenever working in scp/, or whenever the task involves SCPs, organization-level guardrails, tag-enforcement policies, aws:RequestTag conditions, or attaching policies to an OU or account. Also use when explaining SCP behavior, debugging a policy that blocks too much or too little, or planning SCP testing against a sandbox organization.
---

# Authoring and testing SCPs

## The one thing to get right first

**An SCP never grants permission. It only sets the ceiling on what IAM
permissions *can* be effective.** An action is allowed only if the SCP permits
it AND an IAM policy grants it. An `Allow` statement in an SCP does not give
anyone access — it only widens the ceiling.

If you ever explain an SCP as "granting" something, that is wrong and it will be
wrong in an interview too. The right phrasing: *"the SCP defines the maximum
available permissions for accounts in the organization; IAM still has to grant
them separately."*

## Non-obvious behavior that causes real incidents

- **The management account is never affected by SCPs.** Testing an SCP from the
  management account will show it having no effect. This is the single most
  common reason someone thinks their SCP "isn't working." Always test from a
  **member account** inside the target OU.
- **SCPs do not apply to service-linked roles.** AWS services acting on your
  behalf bypass them.
- **`FullAWSAccess` is attached by default** at every level. It is the implicit
  ceiling. If you detach it without replacing it, everything breaks.
- Deny statements are evaluated at **every level** of the OU hierarchy from root
  down. A deny anywhere in the chain wins.
- Changes propagate in seconds but are eventually consistent. Retry once before
  concluding a policy did not apply.

## Tag enforcement — the condition operator matters

To deny creation when a tag is **missing**, use the `Null` operator against
`aws:RequestTag/<key>`:

```json
{
  "Effect": "Deny",
  "Action": "ec2:RunInstances",
  "Resource": "arn:aws:ec2:*:*:instance/*",
  "Condition": {
    "Null": { "aws:RequestTag/owner": "true" }
  }
}
```

`"Null": {"aws:RequestTag/owner": "true"}` reads as *"the key `owner` was NOT
supplied in the request"*. That is the correct test for absence.

**Fail-open traps to check for every time:**

- Using `StringNotEquals` where `Null` is needed. `StringNotEquals` does not
  match when the key is absent, so a request with no tags at all passes straight
  through. This looks correct and silently enforces nothing.
- Multiple keys in one `Null` block are ANDed — the deny fires only when *all*
  listed tags are missing. To require *each* tag independently, use a separate
  statement (or separate condition) per tag.
- `aws:RequestTag` only sees tags supplied **in the create call**. Tagging a
  resource after creation does not satisfy it. That is the intent (it forces
  tag-on-create), but say so explicitly when explaining it.
- `ec2:RunInstances` creates several resource types (instance, volume, network
  interface). Scope `Resource` deliberately, and know that tag-on-create must
  use `TagSpecifications` for each type you gate.
- Blocking RDS requires **both** `rds:CreateDBInstance` and
  `rds:CreateDBCluster`. Blocking only one leaves a bypass.

## Always include a break-glass exemption

Every deny policy should exempt a designated break-glass role, or you can lock
the organization out of its own remediation path:

```json
"Condition": {
  "Null": { "aws:RequestTag/owner": "true" },
  "ArnNotLike": {
    "aws:PrincipalArn": "arn:aws:iam::*:role/OrganizationBreakGlass"
  }
}
```

Scope it to a specific role name. Never wildcard the principal.

## Testing procedure

An SCP is not done until it has been run against a real organization. The setup:

1. Management account with AWS Organizations enabled, **all features** (not
   consolidated billing only — SCPs require all features).
2. A dedicated OU, e.g. `scp-testing`.
3. A member account inside that OU.
4. A role in the member account you can assume with permissions to attempt the
   create calls.

For each rule, run a **deny/allow pair**:

- **Deny case** — create the resource with the tags missing. Expect
  `AccessDenied` with an explicit-deny message.
- **Allow case** — identical call with all required tags present. Expect success.

A test plan with only deny cases proves nothing; it cannot distinguish "the SCP
works" from "the caller had no permission anyway." **The allow case is the
control.** Record the actual CLI output for both.

Use `--dry-run` where the API supports it (EC2 does) to avoid creating billable
resources. Where it does not, clean up immediately after.

## Reviewing an existing SCP

Check, in order:

1. Does any statement deny something that would lock out the management path?
2. Is every condition operator correct for absence vs. mismatch?
3. Does the action list actually cover every API that creates the resource type?
4. Are `Resource` ARNs scoped, or is it `"*"` where that is too broad?
5. Is there a break-glass exemption, scoped narrowly?
6. Does the test plan include a passing allow case for each deny case?
