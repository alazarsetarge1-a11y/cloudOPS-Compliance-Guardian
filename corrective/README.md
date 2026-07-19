# Corrective Layer — SSM Automation Runbooks

Automation runbooks triggered by Detective-layer findings that remediate
violations without human intervention.

This is the **corrective** control — it closes the loop: Config/Boto3 detects
a violation, this layer fixes it.

## Planned contents

- `runbooks/remediate-public-s3.yaml` — SSM Automation document that disables
  public access on a flagged S3 bucket
- `runbooks/remediate-open-sg.yaml` — SSM Automation document that removes
  overly permissive inbound rules from a flagged security group
- `runbooks/remediate-missing-mfa.yaml` — SSM Automation document that
  notifies/flags an IAM user for missing MFA (can't force-enroll, so this one
  is notify-and-track rather than fully automated fix)
- `trigger-mapping.md` — which Detective finding maps to which runbook

## Status

Not yet started. Third layer to build, after Detective is producing real findings.
