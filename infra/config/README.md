# AWS Config — detective layer (Terraform)

Enables AWS Config in the **member account** and deploys managed rules that mirror
the Boto3 checks in `detective/`, one-for-one. Config evaluates rules on resource
change (event-driven) and, for some, on a periodic schedule — `iam-user-mfa-enabled`
and `root-account-mfa-enabled` are periodic — complementing the point-in-time
Boto3 scans.

## Scope

This stack records **one region** (`var.region`, default `us-east-1`). AWS Config
is regional: `all_supported` covers every resource type *within that region*, not
the whole account. Full multi-region coverage would need a recorder + delivery
channel per region (or a Config aggregator) — out of scope for this sandbox, which
only uses us-east-1.

| Boto3 check (`detective/`) | AWS Config managed rule |
|---|---|
| `tag-compliance` | `required-tags` |
| `s3-public-access` | `s3-bucket-level-public-access-prohibited` |
| `iam-mfa` | `iam-user-mfa-enabled`, `root-account-mfa-enabled` |
| `security-groups` | `restricted-ssh` |
| `rds-encryption` | `rds-storage-encrypted` |

## What it creates

An S3 delivery bucket (encrypted, versioned, public-access-blocked), an IAM role
Config assumes, the configuration recorder + delivery channel, and the six rules.

## How the credentials work

The provider authenticates with the local management-account SSO profile (`ccg`)
and **assumes `OrganizationAccountAccessRole`** into the member account — so
everything lands in the member account without a separate login.

## Run it

```bash
aws sso login --profile ccg                 # refresh the management-account SSO session
cp terraform.tfvars.example terraform.tfvars # then set your real 12-digit member account id
terraform -chdir=infra/config init
terraform -chdir=infra/config plan           # preview — changes nothing
terraform -chdir=infra/config apply          # create it
```

## Cost control

AWS Config bills per configuration item recorded and per rule evaluation. In a
near-empty sandbox that's cents, but it's **continuous**. To zero it out when not
demoing:

```bash
terraform -chdir=infra/config destroy
```

## Notes

- `terraform.tfvars` (holding the real account id) is gitignored; only
  `terraform.tfvars.example` (placeholder) is committed.
- `.terraform.lock.hcl` **is** committed — it pins provider versions/checksums.
- State is local (`terraform.tfstate`, gitignored). A remote S3 backend comes
  with the main infra at build Step 6.
