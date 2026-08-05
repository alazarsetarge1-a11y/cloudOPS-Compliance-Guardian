# infra/ecr — container registry (persistent)

Terraform for the ECR repository that holds the backend image. **Persistent
stack** — ECR storage is ~pennies/month, so it stays applied; the image survives
`terraform destroy` of the ephemeral ALB/Fargate stack. Deploys into the member
account (assumes `OrganizationAccountAccessRole` from the `ccg` SSO profile — the
same hub-and-spoke pattern as `infra/config` and `infra/corrective`).

## Design
- `image_tag_mutability = IMMUTABLE` — a pushed tag is permanent; tag images by
  git SHA, never reuse `:latest`.
- `scan_on_push = true` — basic CVE scan on every push (free).
- Lifecycle policy — expire untagged after 1 day, keep the last 10 tagged.

## Apply
```bash
aws sso login --profile ccg                       # if the SSO token expired
cp terraform.tfvars.example terraform.tfvars      # fill in the real member account id
terraform -chdir=infra/ecr init
terraform -chdir=infra/ecr apply
```

## Push an image
```bash
REPO=$(terraform -chdir=infra/ecr output -raw repository_url)
aws ecr get-login-password --profile ccg-member --region us-east-1 \
  | docker login --username AWS --password-stdin "${REPO%/*}"
docker tag ccg-backend:dev "$REPO:$(git rev-parse --short HEAD)"
docker push "$REPO:$(git rev-parse --short HEAD)"
```
`ccg-member` is a local profile that assumes `OrganizationAccountAccessRole` into
the member account (where ECR lives). Cost: storage only (~pennies) — no destroy
needed to control cost.
