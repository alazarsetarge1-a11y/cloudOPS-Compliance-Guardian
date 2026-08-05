# The public front door. Internet-facing, spread across both public subnets (an
# ALB needs >= 2 AZs), wearing the ALB security group.
resource "aws_lb" "backend" {
  # checkov:skip=CKV_AWS_150:Ephemeral stack — deletion protection off so `terraform destroy` works between demos.
  # checkov:skip=CKV_AWS_91:Access logging to S3 omitted for cost in this sandbox.
  # checkov:skip=CKV2_AWS_20:HTTP->HTTPS redirect + HTTPS listener arrive in Stage 4 with CloudFront + the ACM cert.
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

# HTTP listener for Stage 3 testing. Stage 4 replaces this with an HTTPS listener
# (ACM cert) behind CloudFront.
resource "aws_lb_listener" "http" {
  # checkov:skip=CKV_AWS_2:Temporary HTTP listener for Stage 3 testing; replaced by HTTPS + ACM cert in Stage 4.
  # checkov:skip=CKV_AWS_103:No TLS on this temporary HTTP listener; TLS 1.2+ arrives with the HTTPS listener in Stage 4.
  load_balancer_arn = aws_lb.backend.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }
}
