# Persistent frontend stack. us-east-1 is required for CloudFront's ACM cert, and
# it's our region anyway. Same assume-role-into-member pattern as the other stacks.
provider "aws" {
  region  = var.region
  profile = var.profile

  assume_role {
    role_arn     = "arn:aws:iam::${var.member_account_id}:role/OrganizationAccountAccessRole"
    session_name = "terraform-ccg-frontend"
  }

  default_tags {
    tags = {
      owner               = "ccg-platform"
      environment         = "sandbox"
      cost-center         = "cc-1000"
      data-classification = "internal"
      managed-by          = "terraform"
      project             = "cloud-compliance-guardian"
    }
  }
}
