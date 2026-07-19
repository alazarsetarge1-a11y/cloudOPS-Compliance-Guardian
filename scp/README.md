# Preventive Layer — SCP Tag-Compliance Guardrail

Service Control Policy (SCP) applied at the AWS Organizations level that blocks
resource creation (EC2, S3, etc.) when required compliance tags are missing.

This is the **preventive** control — it stops non-compliant resources from ever
being created, rather than catching them after the fact.

## Planned contents

- `deny-untagged-resources.json` — the SCP policy document
- `required-tags.md` — the tag schema this policy enforces (owner, environment,
  cost-center, data-classification, etc.)
- `test-plan.md` — how this was tested (which resource creation calls were
  attempted, which were blocked, which were allowed through)

## Status

Not yet started. First layer to build — no dependencies on the rest of the stack.
