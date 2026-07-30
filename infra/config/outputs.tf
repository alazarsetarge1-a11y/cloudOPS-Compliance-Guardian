output "config_bucket" {
  value       = aws_s3_bucket.config.bucket
  description = "S3 bucket AWS Config delivers to."
}

output "recorder_name" {
  value       = aws_config_configuration_recorder.main.name
  description = "The configuration recorder name."
}

output "managed_rules" {
  value = [
    aws_config_config_rule.required_tags.name,
    aws_config_config_rule.s3_public_access.name,
    aws_config_config_rule.iam_user_mfa.name,
    aws_config_config_rule.root_mfa.name,
    aws_config_config_rule.restricted_ssh.name,
    aws_config_config_rule.rds_storage_encrypted.name,
  ]
  description = "Deployed AWS Config managed rules."
}
