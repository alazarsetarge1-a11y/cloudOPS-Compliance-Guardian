# The ECR image to run — looked up from the ecr stack's repo (same member
# account). image_tag defaults to the git SHA we pushed in Stage 1.
data "aws_ecr_repository" "backend" {
  name = "ccg-backend"
}

# Where the container's stdout/stderr go. Short retention = cost control.
resource "aws_cloudwatch_log_group" "backend" {
  # checkov:skip=CKV_AWS_338:7-day retention is deliberate for cost in this sandbox; a year of logs isn't warranted.
  # checkov:skip=CKV_AWS_158:AWS-managed encryption is sufficient; a KMS CMK adds cost for no benefit (same call as ECR/secret).
  name              = "/ecs/ccg-backend"
  retention_in_days = 7
}

# A cluster is just a logical grouping for Fargate tasks — no servers to manage.
resource "aws_ecs_cluster" "main" {
  # checkov:skip=CKV_AWS_65:Container Insights omitted for cost; not warranted for a single-task sandbox service.
  name = "ccg-backend"
}

# The task definition is the blueprint: which image, how much CPU/RAM, which
# roles, and how config reaches the container.
resource "aws_ecs_task_definition" "backend" {
  family                   = "ccg-backend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc" # Fargate requirement — each task gets its own ENI
  cpu                      = "256"    # 0.25 vCPU
  memory                   = "512"    # 0.5 GB

  # Match the image we built + pushed (Apple Silicon) → cheaper Graviton Fargate.
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "ARM64"
  }

  execution_role_arn = aws_iam_role.execution.arn # agent: pull image, write logs, fetch secret
  task_role_arn      = aws_iam_role.task.arn      # your code: scans + remediation

  container_definitions = jsonencode([
    {
      name      = "ccg-backend"
      image     = "${data.aws_ecr_repository.backend.repository_url}:${var.image_tag}"
      essential = true

      portMappings = [
        { containerPort = var.app_port, protocol = "tcp" }
      ]

      # Non-secret config via plain env vars. (CCG_CORS_ORIGINS is added in Stage 4
      # once the CloudFront domain exists. No CCG_ASSUME_ROLE_ARN — in the member
      # account the task role IS the identity.)
      environment = [
        { name = "CCG_AWS_REGION", value = var.region }
      ]

      # Secret injection: the EXECUTION role fetches this from Secrets Manager and
      # sets it as CCG_API_KEY in the container env. The value is never in the image
      # or the task def — only the secret's ARN is.
      secrets = [
        { name = "CCG_API_KEY", valueFrom = data.aws_secretsmanager_secret.api_key.arn },
        # The assistant's Claude key (read by the anthropic SDK). If it's still the
        # placeholder, the assistant returns 503 and the dashboard is unaffected —
        # graceful degradation, not a container crash.
        { name = "ANTHROPIC_API_KEY", valueFrom = data.aws_secretsmanager_secret.anthropic_api_key.arn },
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.backend.name
          "awslogs-region"        = var.region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])
}
