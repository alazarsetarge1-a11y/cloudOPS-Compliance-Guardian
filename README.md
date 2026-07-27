# Cloud Compliance Guardian

A layered AWS compliance system built around a **Preventive -> Detective -> Corrective** control model, with a live dashboard on top. Instead of just reporting on non-compliant resources, this system stops bad configuration before it happens, continuously watches for anything that slips through, and automatically fixes what it finds.

## Why this project exists

Most compliance-checker projects stop at detection: a script runs, prints a report, someone reads it later. That's not how compliance actually works at scale. This project implements the same three-control-type model used in real GRC and cloud security engineering work:

- **Preventive** — stop violations from being created in the first place
- **Detective** — continuously watch for violations that happen anyway
- **Corrective** — fix violations automatically, without waiting on a human

## Architecture

```
                    ┌─────────────────────────┐
                    │   React Dashboard (UI)  │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   FastAPI Backend (API) │
                    └────────────┬────────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
┌─────────────────┐    ┌──────────────────────┐   ┌──────────────────────┐
│   Preventive    │    │      Detective       │   │      Corrective      │
│   SCP Policy    │    │  AWS Config + Boto3  │   │   SSM Automation     │
│                 │    │  compliance checks   │   │      runbooks        │
│ Blocks resource │    │                      │   │                      │
│ creation w/o    │───▶│ Flags non-compliant  │-> │ Auto-remediates      │
│ required tags   │    │ resources            │   │flagged violations    │
└─────────────────┘    └──────────────────────┘   └──────────────────────┘

                    ┌─────────────────────────┐
                    │  Terraform (deploys all │
                    │  of the above to ECS    │
                    │  Fargate)               │
                    └─────────────────────────┘
```

## Components

| Folder | Layer | What it does |
|---|---|---|
| `scp/` | Preventive | SCP JSON policy blocking resource creation missing required compliance tags |
| `detective/` | Detective | AWS Config rules + Python/Boto3 checks (S3 public access, IAM MFA, open EC2 ports, etc.) |
| `corrective/` | Corrective | SSM Automation runbook definitions that remediate flagged findings |
| `backend/` | API | FastAPI service exposing findings + remediation history as REST endpoints |
| `frontend/` | UI | React + Tailwind dashboard visualizing findings, IAM heatmap, remediation timeline |
| `infra/` | Deployment | Terraform deploying the full stack to ECS Fargate |

## Build status

- [x] Preventive — SCP guardrail *(validated against a live AWS Organization — see `scp/test-plan.md`)*
- [ ] Detective — Config rules + Boto3 checks
- [ ] Corrective — SSM Automation runbooks
- [ ] Backend — FastAPI
- [ ] Frontend — React dashboard
- [ ] Infra — Terraform deployment

## Tech stack

AWS (Config, SSM Automation, Organizations/SCP, IAM, S3, EC2), Python (Boto3, FastAPI), React, Tailwind CSS, Terraform, Docker, ECS Fargate
