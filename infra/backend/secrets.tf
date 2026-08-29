# The backend's API key is OWNED by the PERSISTENT frontend stack (see
# infra/frontend/secrets.tf) so it survives destroy/re-apply of this ephemeral
# stack — the key stays stable and CloudFront's injected value never desyncs.
# Here we only READ it (by name) to wire into the task definition + execution role.
data "aws_secretsmanager_secret" "api_key" {
  name = "ccg/backend/api-key"
}

# The assistant's Anthropic API key is ALSO owned by the persistent stack (set once,
# survives backend teardown; see infra/frontend/secrets.tf). We only READ it here to
# inject into the task definition — the value is fetched by the execution role at
# task start, so a placeholder-only secret still lets the container boot.
data "aws_secretsmanager_secret" "anthropic_api_key" {
  name = "ccg/assistant/anthropic-api-key"
}
