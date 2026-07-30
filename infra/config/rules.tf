# AWS-managed Config rules, one per detective Boto3 check. Config evaluates these
# continuously and event-driven (on resource change) — complementing the
# point-in-time Boto3 scans. Every rule depends on the recorder existing first.

# tag-compliance ↔ required-tags. This is the highest-value complement: unlike
# the Boto3 GetResources approach, the managed rule evaluates resources directly,
# catching never-tagged assets the Boto3 check can miss.
resource "aws_config_config_rule" "required_tags" {
  name = "required-tags"
  source {
    owner             = "AWS"
    source_identifier = "REQUIRED_TAGS"
  }
  input_parameters = jsonencode({
    tag1Key = var.required_tags[0]
    tag2Key = var.required_tags[1]
    tag3Key = var.required_tags[2]
    tag4Key = var.required_tags[3]
  })
  depends_on = [aws_config_configuration_recorder.main]
}

# s3-public-access ↔ s3-bucket-level-public-access-prohibited
resource "aws_config_config_rule" "s3_public_access" {
  name = "s3-bucket-level-public-access-prohibited"
  source {
    owner             = "AWS"
    source_identifier = "S3_BUCKET_LEVEL_PUBLIC_ACCESS_PROHIBITED"
  }
  depends_on = [aws_config_configuration_recorder.main]
}

# iam-mfa ↔ iam-user-mfa-enabled + root-account-mfa-enabled
resource "aws_config_config_rule" "iam_user_mfa" {
  name = "iam-user-mfa-enabled"
  source {
    owner             = "AWS"
    source_identifier = "IAM_USER_MFA_ENABLED"
  }
  depends_on = [aws_config_configuration_recorder.main]
}

resource "aws_config_config_rule" "root_mfa" {
  name = "root-account-mfa-enabled"
  source {
    owner             = "AWS"
    source_identifier = "ROOT_ACCOUNT_MFA_ENABLED"
  }
  depends_on = [aws_config_configuration_recorder.main]
}

# security-groups ↔ restricted-ssh (INCOMING_SSH_DISABLED)
resource "aws_config_config_rule" "restricted_ssh" {
  name = "restricted-ssh"
  source {
    owner             = "AWS"
    source_identifier = "INCOMING_SSH_DISABLED"
  }
  depends_on = [aws_config_configuration_recorder.main]
}

# rds-encryption ↔ rds-storage-encrypted
resource "aws_config_config_rule" "rds_storage_encrypted" {
  name = "rds-storage-encrypted"
  source {
    owner             = "AWS"
    source_identifier = "RDS_STORAGE_ENCRYPTED"
  }
  depends_on = [aws_config_configuration_recorder.main]
}
