# Same hub-and-spoke auth as infra/config: authenticate with the local
# management-account SSO profile (var.profile = "ccg") and assume the
# OrganizationAccountAccessRole into the member account, so every resource this
# stack creates lands in the member account alongside the buckets it remediates.
provider "aws" {
  region  = var.region
  profile = var.profile

  assume_role {
    role_arn     = "arn:aws:iam::${var.member_account_id}:role/OrganizationAccountAccessRole"
    session_name = "terraform-ccg-corrective"
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
