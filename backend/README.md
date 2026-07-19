# Backend — FastAPI

Exposes Detective-layer findings and Corrective-layer remediation history as
REST endpoints for the frontend dashboard to consume.

## Planned endpoints

- `GET /findings` — list current compliance findings
- `GET /findings/{id}` — detail on a single finding
- `GET /remediations` — history of automated remediation actions taken
- `GET /health` — basic health check

## Status

Not yet started. Fourth layer to build, after Detective + Corrective exist to
wrap.
