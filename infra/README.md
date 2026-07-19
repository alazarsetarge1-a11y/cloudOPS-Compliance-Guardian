# Infra — Terraform

Deploys the full stack (backend + frontend) to ECS Fargate, plus any supporting
AWS resources (SQS if used for async remediation triggers, PostgreSQL for
findings storage, etc.).

## Planned contents

- `main.tf` — provider config, root module
- `ecs.tf` — ECS Fargate cluster/service/task definitions for backend + frontend
- `networking.tf` — VPC, subnets, security groups
- `rds.tf` or `dynamodb.tf` — findings/remediation history storage
- `variables.tf` / `outputs.tf`

## Status

Not started. Last layer to build — deployment comes after the application
logic is real and working locally.
