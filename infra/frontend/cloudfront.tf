# The API key CloudFront injects on the /api origin — read from Secrets Manager so
# it always matches what the backend expects. Lives in CloudFront config + TF state
# (local, gitignored), never in the browser. This IS the BFF.
data "aws_secretsmanager_secret_version" "api_key" {
  secret_id = "ccg/backend/api-key"
}

# Managed policies (referenced by name so we don't hardcode ids).
data "aws_cloudfront_cache_policy" "optimized" {
  name = "Managed-CachingOptimized"
}
data "aws_cloudfront_cache_policy" "disabled" {
  name = "Managed-CachingDisabled"
}
data "aws_cloudfront_origin_request_policy" "all_viewer_except_host" {
  name = "Managed-AllViewerExceptHostHeader"
}

# OAC lets CloudFront read the private S3 bucket with SigV4 — no public bucket.
resource "aws_cloudfront_origin_access_control" "site" {
  name                              = "ccg-frontend-oac"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# Strips the /api prefix before forwarding to the ALB origin, so the backend keeps
# serving clean paths (/health, /findings, ...) while CloudFront routes on /api/*.
resource "aws_cloudfront_function" "strip_api_prefix" {
  name    = "ccg-strip-api-prefix"
  runtime = "cloudfront-js-2.0"
  code    = <<-EOT
function handler(event) {
  var request = event.request;
  if (request.uri.indexOf("/api") === 0) {
    request.uri = request.uri.substring(4) || "/";
  }
  return request;
}
EOT
}

resource "aws_cloudfront_distribution" "site" {
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  aliases             = [var.domain_name, "www.${var.domain_name}"]
  price_class         = "PriceClass_100" # US/EU edges only — cost control
  comment             = "CCG frontend"

  # Static app from the private S3 bucket.
  origin {
    origin_id                = "s3-site"
    domain_name              = aws_s3_bucket.site.bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.site.id
  }

  # API from the ALB (via api.<domain>, HTTPS), with the injected key.
  origin {
    origin_id   = "api-alb"
    domain_name = "api.${var.domain_name}"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }

    custom_header {
      name  = "X-API-Key"
      value = data.aws_secretsmanager_secret_version.api_key.secret_string
    }
  }

  # Default: serve the static app, cached at the edge.
  default_cache_behavior {
    target_origin_id       = "s3-site"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    cache_policy_id        = data.aws_cloudfront_cache_policy.optimized.id
    compress               = true
  }

  # /api/* -> the ALB origin: never cache, forward the full request.
  ordered_cache_behavior {
    path_pattern             = "/api/*"
    target_origin_id         = "api-alb"
    viewer_protocol_policy   = "redirect-to-https"
    allowed_methods          = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods           = ["GET", "HEAD"]
    cache_policy_id          = data.aws_cloudfront_cache_policy.disabled.id
    origin_request_policy_id = data.aws_cloudfront_origin_request_policy.all_viewer_except_host.id
    compress                 = true

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.strip_api_prefix.arn
    }
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate_validation.site.certificate_arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }
}
