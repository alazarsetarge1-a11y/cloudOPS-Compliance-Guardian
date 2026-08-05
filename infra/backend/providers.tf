# Base creds are the management-account SSO profile; we ASSUME
# OrganizationAccountAccessRole into the member account, so the whole ephemeral
# backend stack (VPC, SGs, and later ALB + Fargate) lands THERE — the same
# hub-and-spoke pattern as infra/config, infra/corrective, and infra/ecr.
provider "aws" {
  region  = var.region
  profile = var.profile

  assume_role {
    role_arn     = "arn:aws:iam::${var.member_account_id}:role/OrganizationAccountAccessRole"
    session_name = "terraform-ccg-backend"
  }

  # Dogfood the four required tags so our own infra satisfies the deny-untagged SCP.
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
