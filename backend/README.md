# Backend — FastAPI

A thin HTTP transport over the detective/corrective **service layer**. Routes hold
no compliance logic — each wraps a pure function (`run_all_checks`, `summarize`,
`remediate`) — so the same logic backs both this REST API and the Step-7 MCP
server without duplication.

## Endpoints

| Route | Verb | Auth | Wraps |
|---|---|---|---|
| `/health` | GET | none | — (liveness; no AWS calls) |
| `/findings` | GET | **API key** | `run_all_checks` (+ `?status=` / `?severity=` filters) |
| `/compliance-score` | GET | **API key** | `summarize` (counts + score) |
| `/remediations` | POST | **API key** | `remediate` (gated) |

Only `/health` is unauthenticated. Findings expose the account's misconfigurations
and ARNs — a threat map — so the read endpoints require the key too.

Interactive docs at `/docs` (Swagger UI), machine-readable spec at `/openapi.json`
— both auto-generated from the type hints + Pydantic models.

### POST /remediations — the gated, mutating endpoint

```json
{ "check_id": "s3-public-access", "resource_id": "my-bucket", "apply": false }
```

- **Trust model:** the server ignores any client-supplied status and **re-derives
  the finding from a fresh scan**; it acts only if it independently confirms the
  resource is currently `NON_COMPLIANT` (else `404`). A forged/stale "fix this"
  request does nothing.
- **Gate:** `apply` defaults to `false` (dry run → `PLANNED`); `apply: true`
  executes (auto-fixes return `STARTED`, notify checks return `NOTIFIED`).
- **Auth:** requires the `X-API-Key` header (checked against `CCG_API_KEY`,
  constant-time, on encoded bytes so a non-ASCII header is a clean 401). Fails
  **closed** — if no key is configured on the server, the endpoint is disabled
  (`503`), never left open. The same guard protects the read endpoints.

## Configuration (env vars)

| Var | Purpose | Default |
|---|---|---|
| `CCG_AWS_PROFILE` | base AWS profile (local SSO); unset → default cred chain | unset |
| `CCG_ASSUME_ROLE_ARN` | role to assume into the member account | unset |
| `CCG_AWS_REGION` | region for the assumed session | us-east-1 |
| `CCG_API_KEY` | required key for all endpoints except `/health` | unset → those endpoints 503 |

In production on ECS the task role *is* the member-account identity, so no
assume-role is needed and `CCG_API_KEY` is injected from Secrets Manager / SSM.

## Run it locally

All commands are run **from the repository root**:

```bash
python -m venv backend/.venv && . backend/.venv/bin/activate
pip install -r backend/requirements-dev.txt
aws sso login --profile ccg   # for live AWS data

CCG_AWS_PROFILE=ccg \
CCG_ASSUME_ROLE_ARN=arn:aws:iam::<member-account-id>:role/OrganizationAccountAccessRole \
CCG_API_KEY=<your-key> \
PYTHONPATH=. python -m uvicorn app.main:app --app-dir backend --port 8000
```

Then open http://localhost:8000/docs.

## Tests

```bash
pytest backend/tests
```

Fully offline: dependency overrides (`get_findings`, `get_session`) inject canned
data so no test touches real AWS.

## Layout

```text
backend/app/
  main.py            # app + router wiring (thin composition root)
  dependencies.py    # get_session, get_findings (chained DI)
  security.py        # require_api_key (fail-closed)
  schemas.py         # Pydantic request/response models = the API contract
  routers/
    findings.py      # GET /findings, GET /compliance-score
    remediations.py  # POST /remediations
```
