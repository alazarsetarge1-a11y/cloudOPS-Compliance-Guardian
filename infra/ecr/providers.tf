# Base creds are the management-account SSO profile (var.profile = "ccg"); we then
# ASSUME OrganizationAccountAccessRole into the member account, so the ECR repo is
# created THERE — the same hub-and-spoke pattern as infra/config and
# infra/corrective, and the account where the backend + scan target already live.
provider "aws" {
  region  = var.region
  profile = var.profile

  assume_role {
    role_arn     = "arn:aws:iam::${var.member_account_id}:role/OrganizationAccountAccessRole"
    session_name = "terraform-ccg-ecr"
  }

  # Tag everything so it satisfies our own deny-untagged SCP — dogfooding the four
  # required tags on our own infrastructure.
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
