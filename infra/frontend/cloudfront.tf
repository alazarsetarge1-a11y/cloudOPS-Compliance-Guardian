# The API-key value CloudFront injects (from the secret this stack now owns — see
# secrets.tf) is set on the /api origin's custom_header below. This IS the BFF.

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

# Security response headers for the app (HSTS+preload, nosniff, frame-deny,
# referrer policy), attached to the cache behaviors below so every viewer response
# carries them. No CSP here — it needs per-app tuning and would risk breaking the SPA.
resource "aws_cloudfront_response_headers_policy" "security" {
  name = "ccg-security-headers"

  security_headers_config {
    strict_transport_security {
      access_control_max_age_sec = 63072000 # 2 years
      include_subdomains         = true
      preload                    = true
      override                   = true
    }
    content_type_options {
      override = true # X-Content-Type-Options: nosniff
    }
    frame_options {
      frame_option = "DENY"
      override     = true
    }
    referrer_policy {
      referrer_policy = "strict-origin-when-cross-origin"
      override        = true
    }
  }
}

resource "aws_cloudfront_distribution" "site" {
  # checkov:skip=CKV_AWS_68:No WAF — public static portfolio site; WAF is per-request cost not warranted for a sandbox. Enable before prod.
  # checkov:skip=CKV2_AWS_47:No WAFv2 Log4j AMR — follows from no WAF (above).
  # checkov:skip=CKV_AWS_310:No origin failover — single-origin demo; a failover group needs a second origin. Enable before prod.
  # checkov:skip=CKV_AWS_374:No geo restriction — the portfolio site is intentionally globally reachable.
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  aliases             = [var.domain_name, "www.${var.domain_name}"]
  price_class         = "PriceClass_100" # US/EU edges only — cost control
  comment             = "CCG frontend"

  # Standard viewer-access logs → the dedicated private log bucket (see logs.tf).
  logging_config {
    bucket          = aws_s3_bucket.logs.bucket_domain_name
    prefix          = "cloudfront/"
    include_cookies = false
  }

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
      value = aws_secretsmanager_secret_version.api_key.secret_string
    }
  }

  # Default: serve the static app, cached at the edge.
  default_cache_behavior {
    target_origin_id           = "s3-site"
    viewer_protocol_policy     = "redirect-to-https"
    allowed_methods            = ["GET", "HEAD", "OPTIONS"]
    cached_methods             = ["GET", "HEAD"]
    cache_policy_id            = data.aws_cloudfront_cache_policy.optimized.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.security.id
    compress                   = true
  }

  # /api/* -> the ALB origin: never cache, forward the full request.
  ordered_cache_behavior {
    path_pattern               = "/api/*"
    target_origin_id           = "api-alb"
    viewer_protocol_policy     = "redirect-to-https"
    allowed_methods            = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods             = ["GET", "HEAD"]
    cache_policy_id            = data.aws_cloudfront_cache_policy.disabled.id
    origin_request_policy_id   = data.aws_cloudfront_origin_request_policy.all_viewer_except_host.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.security.id
    compress                   = true

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
