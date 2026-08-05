# The backend's API key lives in Secrets Manager — never in the image, never in
# git. Generated here; the ECS execution role injects it into the container at
# start (see the task definition's `secrets` block). Same env var the app reads
# locally (CCG_API_KEY) — only the SOURCE changes, exactly as security.py intends.
#
# Tradeoff to know: random_password puts the generated value into Terraform STATE.
# That's fine here (state is local + gitignored); in production you'd generate the
# value outside Terraform so no secret ever lands in state.
resource "random_password" "api_key" {
  length  = 48
  special = false # keep it URL/header-safe for the X-API-Key header
}

resource "aws_secretsmanager_secret" "api_key" {
  # checkov:skip=CKV_AWS_149:AWS-managed encryption is sufficient for a sandbox demo key; a KMS CMK adds cost for no benefit.
  # checkov:skip=CKV2_AWS_57:No auto-rotation for a static demo API key; rotation needs app-side coordination not warranted here.
  name        = "ccg/backend/api-key"
  description = "X-API-Key value for the CCG backend, injected into the Fargate task."
}

resource "aws_secretsmanager_secret_version" "api_key" {
  secret_id     = aws_secretsmanager_secret.api_key.id
  secret_string = random_password.api_key.result
}
