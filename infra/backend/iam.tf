# Two roles, two very different jobs — the distinction to nail in an interview:
#
#   EXECUTION role — used by the ECS AGENT (infrastructure), before your code
#   runs: pull the image from ECR, write logs to CloudWatch, and fetch the
#   Secrets Manager value to inject. NOT your app's identity.
#
#   TASK role — the identity YOUR CODE runs as. boto3's default credential chain
#   picks it up, so the detective scans + SSM remediation call AWS as this role.
#   Because we deploy IN the member account, the task role IS the member identity
#   — no assume-role needed (matches backend/app/dependencies.py).

data "aws_iam_policy_document" "ecs_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

# ---- Execution role: infra plumbing (ECR pull, logs, secret fetch) ----
resource "aws_iam_role" "execution" {
  name               = "ccg-backend-exec"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

# AWS-managed: ECR pull + CloudWatch Logs — exactly what the agent needs.
resource "aws_iam_role_policy_attachment" "execution_managed" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Let the agent read ONLY our one secret, so it can inject it into the container.
data "aws_iam_policy_document" "execution_secrets" {
  statement {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [aws_secretsmanager_secret.api_key.arn]
  }
}

resource "aws_iam_role_policy" "execution_secrets" {
  name   = "read-api-key-secret"
  role   = aws_iam_role.execution.id
  policy = data.aws_iam_policy_document.execution_secrets.json
}

# ---- Task role: what your code runs as (scans + remediation) ----
resource "aws_iam_role" "task" {
  name               = "ccg-backend-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

# Reads for the detective scan: the AWS-managed SecurityAudit policy is
# purpose-built for read-only security assessment — the right tool for a
# compliance scanner, vs. hand-rolling dozens of Describe/Get actions.
resource "aws_iam_role_policy_attachment" "task_securityaudit" {
  role       = aws_iam_role.task.name
  policy_arn = "arn:aws:iam::aws:policy/SecurityAudit"
}

# Writes for the corrective layer: start the SSM runbooks, read their status,
# and pass ONLY the two corrective roles to SSM — nothing else.
data "aws_iam_policy_document" "task_remediation" {
  # checkov:skip=CKV_AWS_356:The "*" is only on ssm:GetAutomationExecution, which does NOT support resource-level IAM scoping. StartAutomationExecution and iam:PassRole ARE tightly scoped.
  statement {
    sid       = "StartRemediationRunbooks"
    actions   = ["ssm:StartAutomationExecution"]
    resources = ["arn:aws:ssm:${var.region}:${var.member_account_id}:automation-definition/*"]
  }
  statement {
    sid       = "ReadAutomationStatus"
    actions   = ["ssm:GetAutomationExecution"]
    resources = ["*"] # GetAutomationExecution does not support resource-level scoping
  }
  statement {
    sid     = "PassOnlyCorrectiveRolesToSSM"
    actions = ["iam:PassRole"]
    resources = [
      "arn:aws:iam::${var.member_account_id}:role/ccg-remediation-s3-role",
      "arn:aws:iam::${var.member_account_id}:role/ccg-remediation-sg-role",
    ]
    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["ssm.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy" "task_remediation" {
  name   = "run-corrective-runbooks"
  role   = aws_iam_role.task.id
  policy = data.aws_iam_policy_document.task_remediation.json
}
