# The registry that holds the backend container image. PERSISTENT stack: ECR
# storage is a few cents/month, so the repo stays applied and the image survives
# `terraform destroy` of the ephemeral ALB/Fargate stack — no re-push per demo.
resource "aws_ecr_repository" "backend" {
  # checkov:skip=CKV_AWS_136:AES256 at-rest is sufficient for non-sensitive application images in this sandbox; a customer-managed KMS key adds cost and Stage-3 kms:Decrypt wiring for no threat-model benefit here. Revisit if this repo ever holds sensitive artifacts.
  name = var.repository_name

  # IMMUTABLE: a pushed tag can never be overwritten, so a given tag (e.g. a git
  # SHA) always refers to the exact same image — reproducible deploys, and nobody
  # can silently move `:v1` under you. Tradeoff: every build needs a fresh, unique
  # tag; you can't reuse `:latest`.
  image_tag_mutability = "IMMUTABLE"

  # Scan each pushed image for known CVEs (free basic scanning) — fits the
  # project's security posture; results show in the ECR console.
  image_scanning_configuration {
    scan_on_push = true
  }

  # Encrypted at rest (AES256 is the free default; stated explicitly).
  encryption_configuration {
    encryption_type = "AES256"
  }

  # Sandbox convenience: let `terraform destroy` remove the repo even if it still
  # holds images (persistent by intent, but keeps teardown clean if we ever do).
  force_delete = true
}

# Cost + clutter hygiene: don't let old images accumulate forever.
resource "aws_ecr_lifecycle_policy" "backend" {
  repository = aws_ecr_repository.backend.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Expire untagged images after 1 day"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 1
        }
        action = { type = "expire" }
      },
      {
        # An 'any' rule must have the highest rulePriority (evaluated last).
        rulePriority = 2
        description  = "Keep only the 10 most recent tagged images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = { type = "expire" }
      }
    ]
  })
}
