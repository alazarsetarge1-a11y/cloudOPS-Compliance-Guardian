# Same assume-role-into-member pattern as the infra stacks, with the SAME compliance
# default_tags — so every demo resource is correctly TAGGED and the preventive tag SCP
# permits its creation. The resources are non-compliant on a DIFFERENT axis (public
# access / open ingress), which is exactly what the detective layer then catches:
# tagging (preventive) is not a substitute for detection.
provider "aws" {
  region  = var.region
  profile = var.profile

  assume_role {
    role_arn     = "arn:aws:iam::${var.member_account_id}:role/OrganizationAccountAccessRole"
    session_name = "terraform-ccg-demo-violations"
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
