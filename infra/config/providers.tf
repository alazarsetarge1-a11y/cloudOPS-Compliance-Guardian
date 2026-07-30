# The AWS provider. We authenticate with the LOCAL management-account SSO profile
# (var.profile = "ccg") and then ASSUME the OrganizationAccountAccessRole into the
# member account — the same hub-and-spoke pattern the SCP tests and the detective
# runner use. So Terraform's base creds are the management account, but every
# resource it manages lands in the member account.
provider "aws" {
  region  = var.region
  profile = var.profile

  assume_role {
    role_arn     = "arn:aws:iam::${var.member_account_id}:role/OrganizationAccountAccessRole"
    session_name = "terraform-ccg-config"
  }

  # Tag everything this stack creates so it satisfies our own tag policy —
  # dogfooding the four required tags on our own infrastructure.
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
