output "runbook_name" {
  value       = aws_ssm_document.s3_public_access.name
  description = "SSM Automation document name — MUST match RUNBOOK_NAME in corrective/remediations/s3_public_access.py."
}

output "automation_role_arn" {
  value       = aws_iam_role.automation.arn
  description = "Least-privilege role the runbook assumes to set bucket public-access blocks."
}
