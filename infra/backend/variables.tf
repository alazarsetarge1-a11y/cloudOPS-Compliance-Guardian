variable "region" {
  description = "AWS region for the deployment (single-region by design)."
  type        = string
  default     = "us-east-1"
}

variable "profile" {
  description = "Local AWS profile used as the base identity before assuming the member-account role."
  type        = string
  default     = "ccg"
}

variable "member_account_id" {
  description = "Member account that hosts the deployment. Real value lives ONLY in the gitignored terraform.tfvars."
  type        = string

  validation {
    condition     = can(regex("^[0-9]{12}$", var.member_account_id))
    error_message = "member_account_id must be a 12-digit AWS account id."
  }
}

variable "vpc_cidr" {
  description = "CIDR block for the dedicated VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "app_port" {
  description = "Port the FastAPI container listens on (matches the Dockerfile EXPOSE/uvicorn port)."
  type        = number
  default     = 8000
}
