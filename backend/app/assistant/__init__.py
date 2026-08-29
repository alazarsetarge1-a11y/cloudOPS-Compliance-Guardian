"""AI best-practices assistant — deliberately decoupled from live AWS.

No tools, no AWS credentials, no account data ever enters the model's context.
The module is a thin transport over the Claude API; FastAPI is the BFF that
holds ANTHROPIC_API_KEY server-side so the browser never sees it.
"""
