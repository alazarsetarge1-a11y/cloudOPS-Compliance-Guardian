# ---------------------------------------------------------------------------
# Deliberately non-compliant resources that seed the dashboard with real findings.
# NOT part of infra/ — CI's `checkov -d infra` never scans this, by design (these
# resources are SUPPOSED to fail security checks). Everything here is free and
# force-destroyable: `terraform apply` seeds the demo, `terraform destroy` clears it.
# ---------------------------------------------------------------------------

# ===== VIOLATION 1: S3 bucket with Block Public Access fully DISABLED =====
# Tagged (SCP-compliant) but unprotected — the detective `s3-public-access` check
# flags it HIGH. We disable BPA rather than attach a public policy, so the bucket is
# flagged WITHOUT actually exposing data (it stays empty and effectively private).
#
# CAVEAT: the check evaluates the EFFECTIVE (account-level OR bucket-level) BPA. If
# this account has account-level BPA fully enabled, it masks this bucket and the
# check correctly reports COMPLIANT. See README to surface the finding.
resource "aws_s3_bucket" "public_demo" {
  bucket        = "ccg-demo-violation-public-${var.member_account_id}"
  force_destroy = true # empty demo bucket; allow a clean destroy
}

resource "aws_s3_bucket_public_access_block" "public_demo" {
  bucket                  = aws_s3_bucket.public_demo.id
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

# ===== VIOLATION 2: security group open to the world on SSH (22) =====
# A dedicated, empty VPC keeps this self-contained (no dependency on a default VPC).
# The detective `security-groups` check flags 0.0.0.0/0 on a sensitive port as HIGH.
resource "aws_vpc" "demo" {
  cidr_block = "10.99.0.0/16"

  tags = {
    Name = "ccg-demo-violations"
  }
}

resource "aws_security_group" "open_demo" {
  name        = "ccg-demo-violation-open-ssh"
  description = "CCG demo: intentionally world-open on SSH to trigger the detective check"
  vpc_id      = aws_vpc.demo.id

  tags = {
    Name = "ccg-demo-violation-open-ssh"
  }
}

resource "aws_vpc_security_group_ingress_rule" "open_ssh" {
  security_group_id = aws_security_group.open_demo.id
  description       = "Demo violation - world-open SSH (22)"
  ip_protocol       = "tcp"
  from_port         = 22
  to_port           = 22
  cidr_ipv4         = "0.0.0.0/0"
}
