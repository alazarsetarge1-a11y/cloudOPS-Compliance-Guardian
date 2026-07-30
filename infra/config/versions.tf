# Pins the Terraform CLI and provider versions so `init` is reproducible — the
# same code resolves to the same provider on any machine/CI. The resulting
# .terraform.lock.hcl (committed) records exact versions + checksums.
terraform {
  required_version = ">= 1.9"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}
