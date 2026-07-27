# Required tag schema

The preventive SCP (`deny-untagged-resources.json`) blocks creation of the
governed resource types unless **all four** of these tags are supplied *in the
creation call*. This is the tag contract the rest of the system relies on — the
detective layer scans for these, the dashboard groups by them, and cost
reporting attributes spend through them.

| Tag key | Required value | Why it exists — the harm it prevents |
|---|---|---|
| `owner` | An email or team identifier | **Accountability.** When a resource is compromised or misbehaving, this is who gets paged. No owner = orphaned infrastructure nobody dares touch. |
| `environment` | `prod` \| `staging` \| `dev` \| `sandbox` | **Blast radius & policy.** Backup, change-control, and security rules differ per environment. Automation must be able to tell prod from a sandbox before it acts. |
| `cost-center` | A billing/cost-center code | **Cost attribution.** Untagged resources are untraceable spend — the "we pay $40k/mo and can't account for a third of it" problem. |
| `data-classification` | `public` \| `internal` \| `confidential` \| `restricted` | **Compliance & security controls.** Encryption, access, and retention requirements follow from classification. An unclassified store could hold PII with none of the required controls — an audit finding waiting to happen. |

> The SCP enforces tag **presence**, not value correctness. Validating that
> `environment` is one of the allowed values (not `prod-ish`) is a **detective**
> concern (AWS Config / Boto3), because the `Null` condition operator can only
> test whether a key was supplied, not what it equals. Presence at create-time
> is the preventive guarantee; value conformance is checked continuously after.

## Governed create actions

`ec2:RunInstances` · `s3:CreateBucket` · `rds:CreateDBInstance` ·
`rds:CreateDBCluster` · `iam:CreateRole`

## Enforcement notes

- **Tag-on-create only.** `aws:RequestTag` sees only tags supplied *in the
  create request*. Tagging a resource afterward does not satisfy the SCP — by
  design, so the tag debt is never created in the first place.
- **Each tag is required independently.** The SCP uses one `Deny` statement per
  tag (four total). Because multiple keys inside a single `Null` block are
  AND-ed, one combined statement would only deny when *every* tag is missing;
  separate statements give the "deny if *any* tag is missing" behavior we want.
- **`Null`, never `StringNotEquals`.** `Null: true` tests for *absence*, so the
  guardrail **fails closed** on a no-tags request. A `StringNotEquals` check
  would fail *open* — a request with no tags has nothing to compare and slips
  through, silently enforcing nothing.
- **Break-glass exemption (pinned to one account).** Every statement exempts the
  single role `arn:aws:iam::419022575959:role/OrganizationBreakGlass` —
  **pinned to the management account, not wildcarded** across accounts (`::*:`).
  Wildcarding the account would let a same-named role created in *any* member
  account inherit the bypass; pinning closes that. The role is a placeholder to
  be created; until it exists the exemption matches nothing, so the guardrail
  applies to everyone. (Nuance: management-account principals are already exempt
  from all SCPs, so in a larger org the break-glass role would live in a
  dedicated security account — pinning here closes the wildcard and documents
  intent.)
- **EC2 is multi-resource.** `RunInstances` creates an instance, an EBS volume,
  *and* a network-interface, and EC2 evaluates the tag condition **per created
  resource**. The SCP scopes `Resource` to `instance` and `volume` (excluding the
  ephemeral, free network-interface), so a caller must tag **both** the instance
  and the volume on create — `ResourceType=instance` and `ResourceType=volume`
  in `--tag-specifications`. (Validated: an all-tags request that tagged only the
  instance was denied on the untagged NIC until `Resource` was scoped.)
- **S3 caveat (validated empirically).** `s3:CreateBucket` historically did not
  support `aws:RequestTag`. AWS has since added tag-on-create for general-purpose
  buckets (needs `s3:CreateBucket` + `s3:TagResource`). The S3 line is therefore
  verified against a live account in `test-plan.md`, not assumed.
