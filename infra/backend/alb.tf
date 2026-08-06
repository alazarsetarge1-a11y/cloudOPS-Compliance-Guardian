# The public front door. Internet-facing, spread across both public subnets (an
# ALB needs >= 2 AZs), wearing the ALB security group.
resource "aws_lb" "backend" {
  # checkov:skip=CKV_AWS_150:Ephemeral stack — deletion protection off so `terraform destroy` works between demos.
  # checkov:skip=CKV_AWS_91:Access logging to S3 omitted for cost in this sandbox.
  # checkov:skip=CKV2_AWS_20:ALB is CloudFront-only over HTTPS; no public HTTP listener exists to redirect.
  # checkov:skip=CKV2_AWS_28:WAF deliberately skipped (right-sized for a portfolio; backend is only live during demos).
  name                       = "ccg-backend"
  load_balancer_type         = "application"
  internal                   = false
  subnets                    = aws_subnet.public[*].id
  security_groups            = [aws_security_group.alb.id]
  drop_invalid_header_fields = true # free hardening: strip malformed headers
}

# Where the ALB sends traffic. target_type = "ip" because Fargate (awsvpc) registers
# each task's ENI IP, not an EC2 instance. The health check polls /health; only
# targets returning 200 receive traffic.
resource "aws_lb_target_group" "backend" {
  # checkov:skip=CKV_AWS_378:ALB->task hop is HTTP inside the VPC (task SG admits only the ALB); external TLS terminates at CloudFront/ALB in Stage 4.
  name        = "ccg-backend"
  target_type = "ip"
  port        = var.app_port
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id

  health_check {
    path                = "/health"
    matcher             = "200"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
}
