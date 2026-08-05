# These feed Stage 3 (ALB + Fargate), which is added to this same stack.
output "vpc_id" {
  description = "The dedicated VPC id."
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "The two public subnet ids (the ALB and Fargate tasks live here)."
  value       = aws_subnet.public[*].id
}

output "alb_security_group_id" {
  description = "SG for the ALB — attach to the ALB in Stage 3."
  value       = aws_security_group.alb.id
}

output "task_security_group_id" {
  description = "SG for the Fargate task ENI — admits only the ALB SG."
  value       = aws_security_group.task.id
}
