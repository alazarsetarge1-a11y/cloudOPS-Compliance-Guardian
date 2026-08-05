# Same pins as the other infra stacks: 1.x CLI, AWS provider major 6. The exact
# provider version + checksums are locked in the committed .terraform.lock.hcl.
terraform {
  required_version = ">= 1.9, < 2.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}
