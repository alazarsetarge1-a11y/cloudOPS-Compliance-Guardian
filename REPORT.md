# Cloud Compliance Guardian — Final Report

> Living document — sections are filled in as the write-up progresses.

## Overview — the problem

In AWS, the leading cause of breaches is **misconfiguration** — public S3 buckets, security
groups open to the internet, IAM users without MFA, unencrypted databases, and untagged,
untraceable resources. As an account's footprint grows, no human can hand-audit every
resource, and a periodic manual review leaves misconfigurations live for weeks.

**Cloud Compliance Guardian keeps a growing AWS account continuously compliant with a security
baseline — preventing bad configuration where it can, detecting it where it can't, and
remediating it safely — with no manual per-resource auditing.**

It is organized on the **Preventive → Detective → Corrective** control model:

- **Preventive** — an AWS Organizations SCP denies creating S3/EC2/RDS/IAM resources without
  the four required tags, so tag debt is never created.
- **Detective** — AWS Config managed rules (continuous) plus Boto3 checks (on-demand) scan the
  live account for public buckets, open security groups, MFA gaps, unencrypted RDS, and tag
  compliance.
- **Corrective** — SSM Automation runbooks remediate the *safely reversible* findings (behind a
  human-approval gate); the rest are notify-only.

A React dashboard surfaces posture and one-click remediation, and an air-gapped AI assistant
answers AWS best-practice questions. The whole system is deployed live on AWS.

The recurring design principle is **bounding blast radius at every layer**: least-privilege
roles, deny-by-tag at create time, a dry-run gate before any mutation, auto-remediation limited
to changes that can only *tighten* security, and an assistant that can only emit text.

## System design & tech stack

Every choice optimizes for the same three things: **least privilege, reproducibility, and cost
control for a sandbox that must still look production-grade.**

| Layer / component | Technology | Why — and what it's good for |
|---|---|---|
| Preventive | **AWS Organizations SCP** (JSON) | The only control that caps permissions *org-wide* regardless of per-principal IAM — a true guardrail, not a policy someone can forget to attach. |
| Detective (continuous) | **AWS Config managed rules** (Terraform) | AWS-managed, evaluates on resource change — no code to maintain, catches drift continuously. |
| Detective (flexible) | **Python 3.12 + Boto3** | AWS's first-class SDK; checks are pure, unit-testable functions and can be richer than a managed rule (e.g. SSH *and* RDP). On-demand complements Config's continuous evaluation. |
| Corrective | **AWS SSM Automation runbooks** (YAML) | Purpose-built for operational runbooks — step model, assume-role, and an auditable execution history out of the box; runs as a scoped role, not the caller's creds. Chosen over Lambda, which would mean hand-building that scaffolding. |
| Backend API | **FastAPI + Pydantic + uvicorn** | Pydantic makes the request/response schema *be* the API contract (and auto-generates OpenAPI docs); async and lightweight. The service layer is transport-agnostic, so the same functions back the API and could back an MCP server. |
| Frontend | **React + Vite + TypeScript + Tailwind** | Vite = fast builds/HMR; TypeScript = type safety across the API boundary; Tailwind with semantic tokens = a real design system without CSS sprawl. |
| AI assistant | **Anthropic Claude API** (Haiku 4.5) | Managed LLM; Haiku is the cheap tier, ample for best-practice Q&A. Air-gapped (no tools, no account data), so the architecture — not a prompt — is the security control. |
| Compute | **ECS Fargate (ARM64/Graviton)** | Serverless containers — no instances to patch; Graviton is ~20% cheaper; a long-lived container suits a persistent API better than Lambda cold starts. |
| Edge / static | **S3 + CloudFront (OAC), ACM, Route53** | Private bucket served by a global CDN over end-to-end TLS on a custom domain; CloudFront also injects the API key server-side (BFF) so the browser holds no secret. |
| Secrets | **AWS Secrets Manager** | Injected at task start — never in code, image, tfvars, or the browser; rotatable. |
| IaC | **Terraform** (per-stack: config, corrective, ecr, backend, frontend) | Declarative, reviewable, reproducible; separate state lets the *ephemeral* backend be destroyed/recreated without touching the *persistent* frontend — the core cost lever. |
| Packaging | **Docker** (multi-stage, non-root, slim) | Small image + attack surface; non-root so a container escape doesn't start as root. |
| Quality gate | **pre-commit + GitHub Actions + CodeRabbit** | Three layers (local → CI → review); checkov scans the project's own IaC — dogfooding the exact rigor the tool enforces on AWS. |

**The two decisions that matter most:**

1. **Ephemeral backend, persistent frontend.** Separate Terraform stacks let the costly backend
   (ALB + Fargate) be destroyed between demos (~$0) while the static frontend stays up (~$1–2/mo)
   — cost control without losing the live URL.
2. **The BFF seam.** CloudFront injects the API key as an origin header, so the browser bundle
   carries no secret — and that same seam is where real user auth (Cognito) would slot in for
   production.

## Preventive layer

### Why the four required tags

Every governed resource must carry four tags at creation, each preventing a specific
failure:

- **`owner`** (email/team) — *accountability*: who gets paged when a resource is
  compromised or misbehaving; no owner means orphaned infrastructure nobody will touch.
- **`environment`** (`prod`|`staging`|`dev`|`sandbox`) — *blast radius & policy*: backup,
  change-control, and security rules differ per environment, and automation (including
  remediation) must tell prod from a sandbox before it acts.
- **`cost-center`** (billing code) — *cost attribution*: untagged resources are
  untraceable spend.
- **`data-classification`** (`public`|`internal`|`confidential`|`restricted`) —
  *compliance & security controls*: encryption, access, and retention requirements follow
  from the classification; an unclassified store could hold PII with none of the required
  controls.

These four are the contract the whole system relies on — the detective layer scans for
them, the dashboard groups by them, and cost reporting attributes spend through them.
Enforcing them **on create** (via the SCP) means the tag debt is never created in the
first place, rather than chasing untagged resources after the fact.

## Detective layer

### AWS Config managed rules

`required-tags` is the AWS-managed `REQUIRED_TAGS` Config rule, fed your four keys
(`owner`, `environment`, `cost-center`, `data-classification`) with no values, and it
continuously flags any supported resource missing *any* of the four as `NON_COMPLIANT`
— a presence check that complements the create-time SCP.

### Boto3 checks

A set of transport-agnostic, paginated, multi-region Boto3 check functions (one per
rule — S3 public access, open security groups, IAM/root MFA, RDS encryption, tag
compliance) that scan the live account on demand and return uniform `Finding` objects,
failing toward flagging (`ERROR`, never a silent pass) when a resource can't be
evaluated.
