# demo-violations — seed the dashboard with real findings

The detective layer scans the **live** account, so the dashboard only shows findings
when non-compliant resources actually exist. This throwaway stack creates two — each
**tagged** so the preventive tag-SCP permits it, but misconfigured on the security
axis the detective layer catches. That contrast is the point: *correct tagging
(preventive) is not a substitute for detection.*

**This directory is intentionally OUTSIDE `infra/`** so the CI `checkov -d infra` scan
never sees it — these resources are *supposed* to fail security checks. Keeping them
here means the pipeline stays green while the demo stays deliberately broken.

## What it creates

| Resource | Violation | Detective check | Severity | Remediable from UI? |
|---|---|---|---|---|
| `aws_s3_bucket.public_demo` | Block Public Access fully disabled | `s3-public-access` | HIGH | ✅ S3 runbook |
| `aws_security_group.open_demo` | `0.0.0.0/0` ingress on SSH (22) | `security-groups` | HIGH | ✅ SG runbook |

Both map to the two corrective runbooks (`ccg-remediation-s3-role`,
`ccg-remediation-sg-role`), so you can demo the full **detect → Preview → Apply** loop
from the dashboard. The bucket only *disables BPA* (no public policy), so it's flagged
without actually exposing data, and it stays empty.

## Caveat: account-level Block Public Access can mask the S3 finding

`s3-public-access` evaluates the **effective** BPA (account-level OR bucket-level). If
this account already has account-level BPA fully enabled, it masks the demo bucket and
the check correctly reports COMPLIANT. To surface the S3 finding, make sure the
account-level BPA isn't blocking all four flags (S3 console → this account's Block
Public Access settings), or just rely on the SG finding — the SG check has no such
masking.

## Usage

```bash
cd demo-violations
cp terraform.tfvars.example terraform.tfvars   # set member_account_id
terraform init
terraform apply     # seed the violations; findings appear on the dashboard's next scan
# ... demo detection, then Preview → Apply the remediation from the UI ...
terraform destroy   # clear the demo
```

Cost: ~$0 — an empty S3 bucket, a security group, and an empty VPC are all free.
