# Private bucket holding the React build. Never public — only CloudFront reads it
# (via Origin Access Control). Account id keeps the global bucket name unique.
resource "aws_s3_bucket" "site" {
  # checkov:skip=CKV_AWS_21:Versioning a static build synced with --delete only accretes cost; not warranted in a sandbox.
  # checkov:skip=CKV2_AWS_61:No lifecycle rule — the build is fully replaced each deploy; add one before prod.
  # checkov:skip=CKV2_AWS_62:Event notifications aren't needed for a static site bucket.
  # checkov:skip=CKV_AWS_145:AWS-managed SSE is sufficient for public static assets (not secret); a KMS CMK adds cost.
  # checkov:skip=CKV_AWS_144:Cross-region replication is overkill for a rebuildable static site.
  bucket = "ccg-frontend-${var.member_account_id}"
}

resource "aws_s3_bucket_public_access_block" "site" {
  bucket                  = aws_s3_bucket.site.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Only CloudFront (via OAC, scoped to THIS distribution) may GetObject.
data "aws_iam_policy_document" "site" {
  statement {
    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.site.arn}/*"]

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.site.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "site" {
  bucket = aws_s3_bucket.site.id
  policy = data.aws_iam_policy_document.site.json
}
