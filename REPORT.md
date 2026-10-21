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

### Scan performance — fan-out concurrency

The on-demand scan was **network-bound, not CPU-bound**: three of the five checks are
regional and walked every enabled region (~17) one `describe_*` call at a time, and the five
checks ran serially — roughly 50 blocking AWS round-trips stacked end to end, the CPU idle
waiting on each socket. That is exactly the case **thread-based concurrency** is built for: a
blocking Boto3 call releases the GIL, so the I/O waits overlap. (Not multiprocessing — there
is no CPU work to split; not asyncio — Boto3 is synchronous.)

The scan now fans out at two levels: a shared helper runs each regional check's per-region
calls on a thread pool, and the runner runs the five checks concurrently — so the whole scan
takes about as long as the single slowest check instead of the sum of all five. The one
correctness subtlety: a Boto3 `Session` is **not** thread-safe for *creating* clients (a
client, once built, *is* safe to call from many threads), so every client is built through one
lock-guarded factory. Client creation is a fast local operation, so serializing it costs
~nothing while the AWS calls themselves stay fully parallel.

Measured on the live member account, back-to-back, with **byte-for-byte identical output** (69
findings, score 100.0, 0 errors) — faster, not a faster wrong answer:

| | Median scan time | Speedup |
|---|---|---|
| Serial (before) | 31.9 s | — |
| Concurrent (after) | 1.8 s | **~18×** |

This cut the dashboard's cold-load latency from ~30 s to under 2 s without changing a single
check's evaluation logic.

## Backend — the API contract (Pydantic)

The FastAPI backend uses **Pydantic models as the single source of truth for the API
contract**. Each request/response shape (`FindingOut`, `RemediationRequest`,
`AssistantAsk`, …) is declared once as a typed class, and FastAPI derives three things
from that one definition: validation in, serialization out, and the OpenAPI docs.

**Gating data IN (validation).** A model's field constraints *are* the input guardrail:

```python
class RemediationRequest(BaseModel):
    check_id: str = Field(min_length=1, max_length=64)
    resource_id: str = Field(min_length=1, max_length=256)
    apply: bool = False
```

A `POST /remediations` body that is missing `check_id`, sends a number instead of a
string, or exceeds the length cap is rejected with a `422` automatically, *before* the
route runs. (The `AssistantAsk` caps — `question` ≤ 4000 chars, `history` ≤ 12 turns —
are the same mechanism, bounding LLM cost/abuse before the request ever reaches Claude.)

**Shaping data OUT (serialization) → the JSON the frontend reads.** The route returns
`FindingOut` objects and Pydantic emits JSON in exactly the declared shape:

```json
{ "check_id": "s3-public-access", "status": "NON_COMPLIANT", "severity": "HIGH", "...": "..." }
```

**Pydantic is backend-only.** The frontend never imports it — it consumes that JSON,
with **TypeScript types that hand-mirror the same shapes** (`status` is `"COMPLIANT" |
"NON_COMPLIANT" | "ERROR"`, etc.). Those TS types are a separate copy kept in sync
manually: change a Pydantic model and you must update the matching TypeScript type, or
the two drift. Net: **Pydantic does runtime validation on the backend (data in *and*
out); TypeScript gives compile-time safety on the frontend**, trusting the shape Pydantic
guarantees.
