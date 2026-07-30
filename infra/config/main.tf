# Resolved at apply time = the MEMBER account (the provider assumes into it).
# Using this reference instead of a literal keeps the real account id out of the
# repo source; it only ever materializes at runtime and in the gitignored state.
data "aws_caller_identity" "current" {}

# ---------------------------------------------------------------------------
# S3 bucket AWS Config delivers configuration snapshots + rule results to.
# Hardened to satisfy the same controls our detective layer checks for
# (dogfooding): encryption, versioning, and full public-access block.
# ---------------------------------------------------------------------------
resource "aws_s3_bucket" "config" {
  #checkov:skip=CKV_AWS_18:Access logging omitted for a sandbox Config bucket (would need a second log bucket).
  #checkov:skip=CKV_AWS_144:Cross-region replication is overkill for a sandbox Config delivery bucket.
  #checkov:skip=CKV_AWS_145:SSE-S3 (AES256) is sufficient here; a dedicated KMS CMK is out of scope for the sandbox.
  #checkov:skip=CKV2_AWS_61:Lifecycle configuration not required for this short-lived sandbox bucket.
  #checkov:skip=CKV2_AWS_62:S3 event notifications are not needed for a Config delivery bucket.
  bucket        = "ccg-config-${data.aws_caller_identity.current.account_id}"
  force_destroy = true # sandbox: let `terraform destroy` empty + remove it cleanly
}

resource "aws_s3_bucket_public_access_block" "config" {
  bucket                  = aws_s3_bucket.config.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "config" {
  bucket = aws_s3_bucket.config.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "config" {
  bucket = aws_s3_bucket.config.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_ownership_controls" "config" {
  bucket = aws_s3_bucket.config.id
  rule {
    object_ownership = "BucketOwnerEnforced" # disables ACLs entirely
  }
}

# The bucket policy AWS Config needs to check the bucket ACL and write deliveries.
# Scoped to this account via the AWS:SourceAccount condition.
data "aws_iam_policy_document" "config_bucket" {
  statement {
    sid       = "AWSConfigBucketPermissionsCheck"
    effect    = "Allow"
    actions   = ["s3:GetBucketAcl", "s3:ListBucket"]
    resources = [aws_s3_bucket.config.arn]
    principals {
      type        = "Service"
      identifiers = ["config.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "AWS:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }

  statement {
    sid       = "AWSConfigBucketDelivery"
    effect    = "Allow"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.config.arn}/AWSLogs/${data.aws_caller_identity.current.account_id}/Config/*"]
    principals {
      type        = "Service"
      identifiers = ["config.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "s3:x-amz-acl"
      values   = ["bucket-owner-full-control"]
    }
    condition {
      test     = "StringEquals"
      variable = "AWS:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }
}

resource "aws_s3_bucket_policy" "config" {
  bucket = aws_s3_bucket.config.id
  policy = data.aws_iam_policy_document.config_bucket_tls.json
}

# Deny any access to the bucket that isn't over TLS. A bucket-policy Deny is the
# right place: it overrides any future identity-policy Allow. AWS service calls
# (Config) already use HTTPS, so they're unaffected.
data "aws_iam_policy_document" "config_bucket_tls" {
  source_policy_documents = [data.aws_iam_policy_document.config_bucket.json]

  statement {
    sid       = "DenyInsecureTransport"
    effect    = "Deny"
    actions   = ["s3:*"]
    resources = [aws_s3_bucket.config.arn, "${aws_s3_bucket.config.arn}/*"]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
    # Exempt AWS service principals (e.g. Config delivery). AWS can redact the
    # SecureTransport key on service-to-service calls, so without this a valid
    # HTTPS Config write could be caught by the deny.
    condition {
      test     = "Bool"
      variable = "aws:PrincipalIsAWSService"
      values   = ["false"]
    }
  }
}

# ---------------------------------------------------------------------------
# IAM role AWS Config assumes to read your resources and write to the bucket.
# Uses the AWS-managed AWS_ConfigRole policy (least-privilege, service-scoped).
# ---------------------------------------------------------------------------
data "aws_iam_policy_document" "config_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["config.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "config" {
  name               = "ccg-config-role"
  assume_role_policy = data.aws_iam_policy_document.config_assume.json
}

resource "aws_iam_role_policy_attachment" "config" {
  role       = aws_iam_role.config.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWS_ConfigRole"
}

# ---------------------------------------------------------------------------
# The recorder (what to record) + delivery channel (where) + start switch.
# Ordering matters and is enforced with depends_on: recorder → channel → start.
# ---------------------------------------------------------------------------
resource "aws_config_configuration_recorder" "main" {
  name     = "ccg-recorder"
  role_arn = aws_iam_role.config.arn

  recording_group {
    all_supported                 = true # record every supported resource type
    include_global_resource_types = true # + global ones (IAM, etc.)
  }
}

resource "aws_config_delivery_channel" "main" {
  name           = "ccg-delivery"
  s3_bucket_name = aws_s3_bucket.config.id
  depends_on     = [aws_config_configuration_recorder.main, aws_s3_bucket_policy.config]
}

resource "aws_config_configuration_recorder_status" "main" {
  name       = aws_config_configuration_recorder.main.name
  is_enabled = true
  depends_on = [aws_config_delivery_channel.main]
}
