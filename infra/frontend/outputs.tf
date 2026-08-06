output "site_url" {
  description = "The live site."
  value       = "https://${var.domain_name}"
}

output "cloudfront_domain" {
  description = "CloudFront distribution domain (for debugging / direct access)."
  value       = aws_cloudfront_distribution.site.domain_name
}

output "site_bucket" {
  description = "S3 bucket the React build is uploaded to."
  value       = aws_s3_bucket.site.id
}
