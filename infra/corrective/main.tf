# Resolved at apply time = the MEMBER account (the provider assumes into it).
# Used to scope the automation role's permissions to this account's buckets.
data "aws_caller_identity" "current" {}

# ---------------------------------------------------------------------------
# Least-privilege role SSM Automation assumes to RUN the runbook.
# The runbook does not run with the caller's (admin) permissions — it drops to
# this role, which can do exactly two things and nothing else.
# ---------------------------------------------------------------------------
data "aws_iam_policy_document" "automation_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ssm.amazonaws.com"]
    }
    # Confused-deputy protection: only SSM acting on behalf of THIS account may
    # assume the role, not SSM in some other account that learned the role name.
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }
}

resource "aws_iam_role" "automation" {
  name               = "ccg-remediation-s3-role"
  assume_role_policy = data.aws_iam_policy_document.automation_assume.json
}

# The ONLY permissions the runbook needs: read + set a bucket's public-access
# block. Nothing else — no delete, no policy edits, no other services.
data "aws_iam_policy_document" "automation_permissions" {
  statement {
    sid    = "ManageBucketPublicAccessBlock"
    effect = "Allow"
    # NOTE: the IAM action names differ from the S3 API operation names — the
    # API is PutPublicAccessBlock, but the IAM permission is
    # s3:PutBucketPublicAccessBlock (with "Bucket"). Granting the API name gets a
    # silent AccessDenied at runbook execution time.
    actions = [
      "s3:GetBucketPublicAccessBlock",
      "s3:PutBucketPublicAccessBlock",
    ]
    # Buckets are discovered at runtime, so the resource can't be a fixed ARN.
    # A wildcard is acceptable *specifically here* because both actions are
    # MONOTONIC-SECURE — they can only READ or TIGHTEN a bucket's public-access
    # posture, never loosen it. The aws:ResourceAccount condition further bounds
    # the wildcard to buckets owned by this member account.
    resources = ["arn:aws:s3:::*"]
    condition {
      test     = "StringEquals"
      variable = "aws:ResourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }
}

resource "aws_iam_role_policy" "automation" {
  name   = "ccg-remediation-s3-policy"
  role   = aws_iam_role.automation.id
  policy = data.aws_iam_policy_document.automation_permissions.json
}

# ---------------------------------------------------------------------------
# The Automation runbook itself. Content is the corrective-layer YAML, rendered
# with the scoped role ARN so the document's assumeRole points at it — the
# Python handler then only has to pass BucketName.
# ---------------------------------------------------------------------------
resource "aws_ssm_document" "s3_public_access" {
  name            = "ccg-remediate-s3-public-access"
  document_type   = "Automation"
  document_format = "YAML"
  content = templatefile("${path.module}/../../corrective/runbooks/remediate-s3-public-access.yaml", {
    automation_role_arn = aws_iam_role.automation.arn
  })
}

# ---------------------------------------------------------------------------
# Security-group remediation: its OWN least-privilege role (each runbook gets a
# role scoped to exactly what it needs — the S3 role can't touch EC2, and this
# one can't touch S3). Reuses the shared ssm.amazonaws.com trust policy above.
# ---------------------------------------------------------------------------
resource "aws_iam_role" "sg_automation" {
  name               = "ccg-remediation-sg-role"
  assume_role_policy = data.aws_iam_policy_document.automation_assume.json
}

data "aws_iam_policy_document" "sg_permissions" {
  # The mutating action, scoped to security groups in THIS account. Revoke only
  # removes ingress rules — it cannot grant access — and the runbook is surgical
  # about which rules it touches.
  statement {
    sid       = "RevokeIngress"
    effect    = "Allow"
    actions   = ["ec2:RevokeSecurityGroupIngress"]
    resources = ["arn:aws:ec2:*:${data.aws_caller_identity.current.account_id}:security-group/*"]
  }
  # Read-only, needed for the runbook's guard (re-describe before revoking).
  # DescribeSecurityGroups has no resource-level scoping, so it must be "*".
  statement {
    sid       = "DescribeForGuard"
    effect    = "Allow"
    actions   = ["ec2:DescribeSecurityGroups"]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "sg_automation" {
  name   = "ccg-remediation-sg-policy"
  role   = aws_iam_role.sg_automation.id
  policy = data.aws_iam_policy_document.sg_permissions.json
}

resource "aws_ssm_document" "security_groups" {
  name            = "ccg-remediate-security-groups"
  document_type   = "Automation"
  document_format = "YAML"
  content = templatefile("${path.module}/../../corrective/runbooks/remediate-security-groups.yaml", {
    automation_role_arn = aws_iam_role.sg_automation.arn
  })
}
