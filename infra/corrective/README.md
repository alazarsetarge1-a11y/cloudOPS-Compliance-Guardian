# Corrective — SSM Automation runbooks (Terraform)

Deploys the corrective layer's remediation runbooks into the **member account**,
alongside the resources they fix. Currently one runbook:

| Detective finding | Runbook (SSM Automation) | What it does |
|---|---|---|
| `s3-public-access` | `ccg-remediate-s3-public-access` | Re-enables all four S3 Block Public Access flags on the flagged bucket |

## What it creates

- An **SSM Automation document** rendered from
  [`corrective/runbooks/remediate-s3-public-access.yaml`](../../corrective/runbooks/remediate-s3-public-access.yaml).
- A **least-privilege IAM role** the runbook assumes — it can only
  `Get`/`PutPublicAccessBlock`, scoped to this account's buckets. The runbook
  does **not** run with the caller's admin permissions.

## How the pieces connect

```text
detective s3-public-access check ──emits──▶ Finding(check_id="s3-public-access")
                                               │
corrective.remediator.remediate(finding, apply=True)
                                               │  ssm:StartAutomationExecution
                                               ▼
        this runbook ──assumes──▶ ccg-remediation-s3-role ──▶ s3:PutPublicAccessBlock
```

The Python handler (`corrective/remediations/s3_public_access.py`) hardcodes the
document name as `RUNBOOK_NAME`; it must equal the `runbook_name` output here.

## Run it

```bash
aws sso login --profile ccg
cp terraform.tfvars.example terraform.tfvars   # set your real member account id
terraform -chdir=infra/corrective init
terraform -chdir=infra/corrective plan
terraform -chdir=infra/corrective apply
```

## Cost

An SSM Automation document and an IAM role cost **nothing** to keep. You are
billed only per Automation step executed, and the first pool of steps each month
is free — so idle cost here is effectively $0 (unlike infra/config, which records
continuously). No urgent need to `destroy` this one.

## Notes

- `terraform.tfvars` (real account id) is gitignored; only the `.example`
  (placeholder) is committed.
- Single-region (`var.region`, default us-east-1), matching infra/config.
- State is local; a remote backend comes with the main infra at build Step 6.
