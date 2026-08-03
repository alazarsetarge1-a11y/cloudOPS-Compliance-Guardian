# Frontend — React Dashboard

Vite + React + TypeScript + Tailwind. Consumes the backend API (findings, score,
gated remediation) and renders the compliance posture. Design rules live in the
`dashboard-design-system` skill: semantic tokens (never raw hex/px), a deliberate
visual hierarchy, and every data view implements loading / error / empty / loaded.

## Views

- **Posture header** — the dominant "is anything on fire?" element (critical+high
  count) + the compliance score + severity breakdown.
- **Findings list** — a designed table: severity stripe as the leading anchor,
  sorted severity-first, status filters, rows expand to reveal the evidence
  payload + ARN + detail.
- **Remediation action** — inside a finding: **Preview** (dry run → the plan),
  then **Apply** — the corrective loop, from the browser. Auto-fixable findings
  get an Apply button; notify-only findings show "flagged for manual review".

Planned next (each needs a backend prerequisite first): **IAM risk heatmap**
(needs richer IAM dimensions in the detective layer) and **remediation timeline**
(needs a persistence layer for history).

## Architecture

- **Tokens** (`src/index.css` + `tailwind.config.js`): CSS custom properties
  surfaced as semantic Tailwind classes; dark mode is a variable swap.
- **Data layer**: a typed `apiGet`/`apiPost` client (`src/lib/api.ts`) adds the
  base URL + `X-API-Key`; hooks (`useApiResource`, `useFindings`,
  `useComplianceScore`, `useRemediation`) own fetching. Components are
  presentational — they take props and never fetch.

## Configuration

Copy `.env.example` to `.env.local` and set:

| Var | Purpose |
|---|---|
| `VITE_API_BASE` | backend base URL (default `http://localhost:8000`) |
| `VITE_API_KEY` | the `X-API-Key` sent on every request |

**`VITE_*` vars are inlined into the build — not secret.** The key only gates
casual access in dev; production would front the API with real user auth
(Cognito), not a browser-embedded key.

## Run it

```bash
npm install
npm run dev        # http://localhost:5173
npm run build      # typecheck (tsc) + production build
npm run test       # component tests (vitest run)
npm run typecheck  # type-check app + test files (tsconfig.test.json)
```

The backend must be running with CORS allowing the dev origin (see the backend
README) and reachable at `VITE_API_BASE`.
