# The backend's API key is OWNED by the PERSISTENT frontend stack (see
# infra/frontend/secrets.tf) so it survives destroy/re-apply of this ephemeral
# stack — the key stays stable and CloudFront's injected value never desyncs.
# Here we only READ it (by name) to wire into the task definition + execution role.
data "aws_secretsmanager_secret" "api_key" {
  name = "ccg/backend/api-key"
}
