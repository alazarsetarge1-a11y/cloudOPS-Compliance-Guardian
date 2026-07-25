# Cloud Compliance Guardian — working context

## What this project is

A layered AWS compliance system built on the **Preventive → Detective → Corrective**
control model, with a React dashboard on top. It is Alazar's flagship portfolio
project for the Aug–Oct 2026 cloud-security internship recruiting cycle
(Deloitte Risk & Financial Advisory Cyber, Dell SRO, AllianceBernstein).

Repo: https://github.com/alazarsetarge1-a11y/cloudOPS-Compliance-Guardian

| Folder | Layer | Role |
|---|---|---|
| `scp/` | Preventive | SCP denying resource creation without required compliance tags |
| `detective/` | Detective | AWS Config rules + Boto3 checks against a compliance baseline |
| `corrective/` | Corrective | SSM Automation runbooks that auto-remediate findings |
| `backend/` | API | FastAPI exposing findings + remediation history |
| `frontend/` | UI | React + Tailwind dashboard |
| `infra/` | Deploy | Terraform → ECS Fargate |

## How to work with Alazar — non-negotiable

These outrank speed. Do not shortcut them.

1. **Teach, don't just deliver.** He must be able to walk through any part of
   this project in a technical interview with zero notes. Explain what each
   piece does *and why that choice over the alternative*. Check understanding
   as you go instead of assuming it. If he says "wym" or seems lost, **stop and
   re-explain** — do not push forward.
2. **Never hand over a wall of finished code.** Build in reviewable pieces and
   explain each one before moving on.
3. **The dashboard UI bar is high.** This is what a recruiter looks at first.
   No default-Bootstrap admin panel. Real design system, real visual hierarchy,
   real data visualization — not tables with a chart bolted on. See
   `.claude/skills/dashboard-design-system/`.
4. **It must actually be deployed.** A live URL for the resume/LinkedIn, not
   "Terraform I never ran." Deployment is a deliverable, not an optional step.
5. **Costs must be itemized and defensible.** A real AWS cost breakdown he
   could defend in an interview, not a guess.
6. **Be honest about state.** If something is claimed done but isn't in the
   repo, say so immediately. Never fill a gap with a plausible-sounding
   assumption about what exists.

His background: AWS SAA-certified, comfortable with Python/Boto3, C++, and
pentesting tools (SQLMap, Burp, nmap, WPScan). Has built CIS Benchmark
automation and a Wazuh SIEM setup. Solid on git/GitHub. **AWS Organizations and
SCPs are newer territory — walk through those step by step.**

## Build order

1. **Preventive (SCP)** — write the policy, then actually run the test plan
   against a real sandbox AWS Organization. Not done until results are filled in.
2. **Detective** — Config rules + Boto3 checks, written fresh for this repo
   (not a port of the old CIS Benchmark script).
3. **Corrective** — SSM Automation runbooks mapped 1:1 to detective findings.
4. **Backend** — FastAPI over findings + remediations.
5. **Frontend** — React + Tailwind dashboard. Highest quality bar.
6. **Infra** — Terraform, then *actually deploy* to ECS Fargate.
7. **Cost breakdown** doc.
8. **Final full-stack report** — architecture decisions, per-layer walkthrough,
   tradeoffs, costs, what to extend next. Feeds resume bullets and interview
   answers.

## Current state (verified 2026-07-21)

- Scaffold: six folders with scoping READMEs, root README with architecture
  diagram, `.gitignore`, `backend/requirements.txt` (fastapi, uvicorn, boto3,
  pydantic, python-dotenv). One commit: `f921e2e`.
- **Preventive layer: NOT started.** `scp/` contains only `README.md`. The
  policy JSON, tag schema doc, and test plan described in earlier planning were
  never written to disk.
- Detective, corrective, backend, frontend, infra: not started. Their
  subdirectories exist locally but are empty (so absent from GitHub).
- Quality gate: pre-commit + GitHub Actions CI + CodeRabbit configured.

## The quality gate — three layers

Bad code is blocked at three points. Each catches what the previous one misses.

1. **Local — pre-commit** (`.pre-commit-config.yaml`). Runs on `git commit`.
   gitleaks, ruff, bandit, checkov, JSON/YAML validation, conventional commits.
   Fast feedback, but bypassable with `--no-verify` and only sees staged files.
2. **CI — GitHub Actions** (`.github/workflows/ci.yml`). Runs on every PR,
   on GitHub's machine, over the whole tree. The `CI gate` job is the single
   required status check. **This is what actually blocks a merge.**
3. **Review — CodeRabbit** (`.coderabbit.yaml`). AI review on every PR with
   per-directory instructions tuned to each layer's real failure modes
   (SCP fail-open conditions, unpaginated Boto3 calls, non-idempotent runbooks,
   Tailwind utility soup).

`main` is branch-protected: no direct pushes, no force pushes. All work goes
through a PR. Workflow:

```bash
git switch -c feat/detective-s3-public-access
# ... work ...
git commit -m "feat(detective): add S3 public access check"
git push -u origin HEAD
gh pr create --fill
```

Commit messages follow Conventional Commits (`feat:`, `fix:`, `docs:`,
`refactor:`, `test:`, `chore:`, `ci:`) — enforced by the commit-msg hook.

## Environment

macOS arm64. Installed: node 26, npm 11, aws-cli 2.36, gh 2.96, pre-commit 4.6,
actionlint, terraform 1.15.8 (hashicorp/tap), Docker, git.

Python: the shell default is 3.14 (python.org, via `.zprofile`). The project
deliberately uses **Python 3.12** (`brew install python@3.12`) for the venv, so
that local == CI == container. Version parity across environments is the point;
3.14 locally against 3.12 in CI is how "works on my machine" happens.

Backend uses a venv at `backend/.venv`.
