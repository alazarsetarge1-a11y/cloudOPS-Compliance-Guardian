# Dedicated, private access-log sink for the CloudFront distribution and the site
# bucket. A log terminus doesn't log itself and doesn't need versioning/replication,
# so those "harden this bucket" checks are consciously skipped here — documented
# sandbox tradeoffs, the same pattern used elsewhere in this repo.
resource "aws_s3_bucket" "logs" {
  # checkov:skip=CKV_AWS_18:This IS the access-log bucket — logging it to itself is a loop.
  # checkov:skip=CKV_AWS_21:Versioning a write-once log sink only accretes cost.
  # checkov:skip=CKV2_AWS_61:No lifecycle rule — sandbox log volume is tiny; add expiry before prod.
  # checkov:skip=CKV2_AWS_62:Event notifications aren't needed for a passive log sink.
  # checkov:skip=CKV_AWS_145:AWS-managed SSE (AES256) is sufficient for access logs; a KMS CMK adds cost.
  # checkov:skip=CKV_AWS_144:Cross-region replication is overkill for sandbox logs.
  bucket = "ccg-frontend-logs-${var.member_account_id}"
}

resource "aws_s3_bucket_public_access_block" "logs" {
  bucket                  = aws_s3_bucket.logs.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ACLs enabled (owner-preferred) so CloudFront standard logging can self-grant its
# log-delivery ACL. S3 server access logs are authorized by the bucket policy below,
# not an ACL, which keeps this bucket free of an explicit (drift-prone) ACL resource.
resource "aws_s3_bucket_ownership_controls" "logs" {
  # checkov:skip=CKV2_AWS_65:ACLs must be ENABLED (owner-preferred) — CloudFront standard logging delivers via a log-delivery ACL grant. The bucket stays private via its public access block.
  bucket = aws_s3_bucket.logs.id
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Authorize S3 server access logging to write the site bucket's logs under s3/.
# Scoped to this account + the site bucket as the only source.
data "aws_iam_policy_document" "logs" {
  statement {
    sid = "S3ServerAccessLogsDelivery"
    principals {
      type        = "Service"
      identifiers = ["logging.s3.amazonaws.com"]
    }
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.logs.arn}/s3/*"]
    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = [aws_s3_bucket.site.arn]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [var.member_account_id]
    }
  }
}

resource "aws_s3_bucket_policy" "logs" {
  bucket = aws_s3_bucket.logs.id
  policy = data.aws_iam_policy_document.logs.json
}

# Point the site bucket's server access logs at the log bucket (satisfies CKV_AWS_18).
resource "aws_s3_bucket_logging" "site" {
  bucket        = aws_s3_bucket.site.id
  target_bucket = aws_s3_bucket.logs.id
  target_prefix = "s3/"
}
