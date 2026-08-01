# Same constraints as infra/config — see that module's versions.tf for the
# reasoning on required_version being a range, not an exact CLI pin.
terraform {
  required_version = ">= 1.9, < 2.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}
