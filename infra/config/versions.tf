# Constrains the Terraform CLI to the 1.x line and pins the provider MAJOR.
# Note: required_version is a *range*, not an exact CLI pin — it just rejects
# incompatible CLIs. What's truly pinned (exact versions + checksums) is the
# committed .terraform.lock.hcl, which locks provider resolution.
terraform {
  required_version = ">= 1.9, < 2.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}
