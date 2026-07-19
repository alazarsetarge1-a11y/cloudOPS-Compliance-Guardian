# Detective Layer — AWS Config + Compliance Checks

Continuously evaluates deployed AWS resources against a compliance baseline.
Rewritten from scratch (not reusing the old CIS Benchmark script) as the
foundation of this layer.

This is the **detective** control — it doesn't fix anything itself, it flags
what's out of compliance so the corrective layer can act on it.

## Planned contents

- `checks/s3_public_access.py` — flags publicly accessible S3 buckets
- `checks/iam_mfa.py` — flags IAM users without MFA enabled
- `checks/ec2_open_ports.py` — flags security groups with overly permissive
  inbound rules (e.g. 0.0.0.0/0 on 22 or 3389)
- `config_rules/` — AWS Config custom rule definitions wrapping the above checks
- `findings_schema.md` — the shape of a "finding" object emitted by this layer,
  which the backend will consume

## Status

Not yet started. Second layer to build, after the SCP.
