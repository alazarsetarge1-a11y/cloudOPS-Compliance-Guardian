# Keeps one copy of the task running and registers it into the ALB target group.
# This is where the no-NAT design is made concrete: assign_public_ip = true.
resource "aws_ecs_service" "backend" {
  # checkov:skip=CKV_AWS_333:Public IP is deliberate (no-NAT architecture); the task SG admits only the ALB, so the task is addressable but not reachable.
  name            = "ccg-backend"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.task.id]
    assign_public_ip = true # no NAT — the task needs a public IP to reach ECR/STS/SSM
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.backend.arn
    container_name   = "ccg-backend"
    container_port   = var.app_port
  }

  # Give uvicorn time to boot (image pull + imports) before the ALB judges /health.
  health_check_grace_period_seconds = 60

  # The target group must be attached to a listener before the service registers.
  depends_on = [aws_lb_listener.http]
}
