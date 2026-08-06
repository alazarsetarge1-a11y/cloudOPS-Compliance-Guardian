# The backend's API key — OWNED here in the PERSISTENT stack so it survives
# destroy/re-apply of the ephemeral backend. That keeps the key STABLE: CloudFront's
# injected value (cloudfront.tf) never desyncs from what the backend expects, and
# tearing the backend down never reserves the secret name. The backend only READS
# this (via a data source). recovery_window_in_days = 0 → a delete is immediate in
# this sandbox (no 30-day name reservation).
resource "random_password" "api_key" {
  length  = 48
  special = false # URL/header-safe for the X-API-Key header
}

resource "aws_secretsmanager_secret" "api_key" {
  # checkov:skip=CKV_AWS_149:AWS-managed encryption is sufficient for a sandbox demo key; a KMS CMK adds cost for no benefit.
  # checkov:skip=CKV2_AWS_57:No auto-rotation for a static demo API key; rotation needs app-side coordination not warranted here.
  name                    = "ccg/backend/api-key"
  description             = "X-API-Key for the CCG backend. Owned by the persistent stack; injected by CloudFront, read by the Fargate task."
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "api_key" {
  secret_id     = aws_secretsmanager_secret.api_key.id
  secret_string = random_password.api_key.result
}
