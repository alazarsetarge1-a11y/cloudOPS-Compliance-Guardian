output "repository_url" {
  description = "Push target: <account>.dkr.ecr.<region>.amazonaws.com/<repo>. Feeds `docker tag`/`push` and the ECS task definition image reference in Stage 3."
  value       = aws_ecr_repository.backend.repository_url
}

output "repository_arn" {
  description = "ARN of the ECR repository (referenced by the task execution role's pull permissions in Stage 3)."
  value       = aws_ecr_repository.backend.arn
}
