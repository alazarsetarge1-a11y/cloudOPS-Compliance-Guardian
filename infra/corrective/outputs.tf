output "runbook_name" {
  value       = aws_ssm_document.s3_public_access.name
  description = "SSM Automation document name — MUST match RUNBOOK_NAME in corrective/remediations/s3_public_access.py."
}

output "automation_role_arn" {
  value       = aws_iam_role.automation.arn
  description = "Least-privilege role the S3 runbook assumes to set bucket public-access blocks."
}

output "sg_runbook_name" {
  value       = aws_ssm_document.security_groups.name
  description = "SSM Automation document name — MUST match RUNBOOK_NAME in corrective/remediations/security_groups.py."
}

output "sg_automation_role_arn" {
  value       = aws_iam_role.sg_automation.arn
  description = "Least-privilege role the security-group runbook assumes to revoke world-open ingress."
}
