# Inputs. member_account_id has NO default on purpose: it's a real identifier we
# keep out of the repo, so you must supply it via terraform.tfvars (gitignored)
# or -var. The regex validation fails fast on a typo'd account id.
variable "member_account_id" {
  type        = string
  description = "12-digit AWS member account to enable Config in (set in terraform.tfvars)."

  validation {
    condition     = can(regex("^[0-9]{12}$", var.member_account_id))
    error_message = "member_account_id must be a 12-digit AWS account id."
  }
}

variable "region" {
  type        = string
  default     = "us-east-1"
  description = "Region for the Config recorder and delivery bucket."
}

variable "profile" {
  type        = string
  default     = "ccg"
  description = "Local AWS profile (management-account SSO) used to assume into the member account."
}

variable "required_tags" {
  type        = list(string)
  default     = ["owner", "environment", "cost-center", "data-classification"]
  description = "Tag keys the required-tags Config rule enforces — mirrors the preventive SCP."

  # The REQUIRED_TAGS managed rule takes exactly four keys, and rules.tf indexes
  # [0..3], so an override with a different count would fail at plan time with an
  # opaque index error. Fail fast with a clear message instead.
  validation {
    condition     = length(var.required_tags) == 4
    error_message = "required_tags must contain exactly four tag keys."
  }
}
