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

# --- Anthropic API key for the AI best-practices assistant (Step 7) ---
# Also OWNED by the persistent stack (like the API key) so you set the real value
# ONCE and it survives destroy/re-apply of the ephemeral backend. The backend only
# READS it. Terraform creates the secret plus a PLACEHOLDER version so the container
# always has a value to fetch — a task can't start if a referenced secret has no
# AWSCURRENT version, and a missing assistant key must NOT take the whole backend
# down. You then set the REAL key out-of-band, so the credential never enters tfvars
# or Terraform state:
#
#   aws secretsmanager put-secret-value \
#     --secret-id ccg/assistant/anthropic-api-key \
#     --secret-string 'sk-ant-...' --profile ccg --region us-east-1
#
# Until the real key is set, the assistant returns 503 (handled) and the dashboard is
# unaffected — the graceful-degradation seam.
resource "aws_secretsmanager_secret" "anthropic_api_key" {
  # checkov:skip=CKV_AWS_149:AWS-managed encryption is sufficient for a sandbox demo secret; a KMS CMK adds cost for no benefit.
  # checkov:skip=CKV2_AWS_57:No auto-rotation — this is a manually-managed third-party API key, not an AWS-native credential.
  name                    = "ccg/assistant/anthropic-api-key"
  description             = "Anthropic API key for the CCG best-practices assistant. Value set out-of-band; read by the Fargate task."
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "anthropic_api_key" {
  secret_id     = aws_secretsmanager_secret.anthropic_api_key.id
  secret_string = "unset-set-via-put-secret-value" # placeholder; real key set out-of-band

  lifecycle {
    # The real key is set with `aws secretsmanager put-secret-value` (see above), which
    # creates a new AWSCURRENT version Terraform doesn't manage. Ignore it so applies
    # stay clean and the real credential never has to enter Terraform state.
    ignore_changes = [secret_string]
  }
}
