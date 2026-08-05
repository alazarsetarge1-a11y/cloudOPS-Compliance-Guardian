# ALB security group — the public entry point. For now allow HTTPS from anywhere
# so we can test end-to-end at Stage 3; Stage 4 tightens ingress to CloudFront's
# origin-facing managed prefix list so the ALB can't be reached around the CDN.
resource "aws_security_group" "alb" {
  # checkov:skip=CKV2_AWS_5:Attached to the ALB in Stage 3 — this ephemeral stack is built incrementally in the same dir.
  name        = "ccg-backend-alb"
  description = "ALB: HTTPS ingress, egress to the task ENIs"
  vpc_id      = aws_vpc.main.id

  tags = { Name = "ccg-backend-alb" }
}

resource "aws_vpc_security_group_ingress_rule" "alb_https" {
  security_group_id = aws_security_group.alb.id
  description       = "HTTPS from the internet (tightened to the CloudFront prefix list in Stage 4)"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_vpc_security_group_egress_rule" "alb_all" {
  security_group_id = aws_security_group.alb.id
  description       = "All egress (forward to the task ENIs)"
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}

# Task security group — THE wall around the Fargate task ENI. Inbound is admitted
# ONLY from the ALB's security group, so even though the task gets a public IP in
# the public subnet, nothing on the internet can reach it directly. Egress stays
# open so the task can call STS/SSM/ECR for its scans + remediation.
resource "aws_security_group" "task" {
  # checkov:skip=CKV2_AWS_5:Attached to the Fargate task ENI in Stage 3 — this ephemeral stack is built incrementally in the same dir.
  name        = "ccg-backend-task"
  description = "Fargate task: inbound only from the ALB SG; open egress to AWS APIs"
  vpc_id      = aws_vpc.main.id

  tags = { Name = "ccg-backend-task" }
}

resource "aws_vpc_security_group_ingress_rule" "task_from_alb" {
  security_group_id = aws_security_group.task.id
  description       = "App port from the ALB only (SG-references-SG)"
  ip_protocol       = "tcp"
  from_port         = var.app_port
  to_port           = var.app_port
  # The wall: source is the ALB's SG, not a CIDR.
  referenced_security_group_id = aws_security_group.alb.id
}

resource "aws_vpc_security_group_egress_rule" "task_all" {
  security_group_id = aws_security_group.task.id
  description       = "All egress (STS/SSM/ECR + the multi-region scans)"
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}

# Lock the VPC's default SG to deny everything — defense in depth so no resource
# ever silently falls back to a permissive default. No rule blocks = deny all.
resource "aws_default_security_group" "default" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "ccg-backend-default-locked" }
}
