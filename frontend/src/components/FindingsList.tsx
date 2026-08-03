import { type ReactNode, useMemo, useState } from "react";

import type { Finding, Severity, Status } from "../types";
import { SeverityBadge, StatusBadge } from "./badges";
import { RemediationPanel } from "./RemediationPanel";

const SEV_RANK: Record<Severity, number> = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };

// Full class strings (static) so Tailwind emits them.
const SEV_STRIPE: Record<Severity, string> = {
  CRITICAL: "border-l-severity-critical",
  HIGH: "border-l-severity-high",
  MEDIUM: "border-l-severity-medium",
  LOW: "border-l-severity-low",
};

type StatusFilter = Status | "ALL";
const FILTERS: { value: StatusFilter; label: string }[] = [
  { value: "NON_COMPLIANT", label: "Non-compliant" },
  { value: "ERROR", label: "Error" },
  { value: "COMPLIANT", label: "Compliant" },
  { value: "ALL", label: "All" },
];

const PANEL = "rounded-2xl border border-line bg-surface-panel shadow-sm";

interface FindingsListProps {
  findings: Finding[] | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
}

export function FindingsList({ findings, loading, error, onRetry }: FindingsListProps) {
  const [status, setStatus] = useState<StatusFilter>("NON_COMPLIANT");
  const [openKey, setOpenKey] = useState<string | null>(null);

  const rows = useMemo(() => {
    const list = (findings ?? []).filter((f) => status === "ALL" || f.status === status);
    // Sort by severity (critical first), then resource for a stable order.
    return [...list].sort(
      (a, b) =>
        SEV_RANK[a.severity] - SEV_RANK[b.severity] ||
        a.resource_id.localeCompare(b.resource_id),
    );
  }, [findings, status]);

  return (
    <section aria-label="Findings" className={PANEL}>
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-5 py-3">
        <h2 className="text-sm font-semibold text-ink">Findings</h2>
        <div role="group" aria-label="Filter by status" className="flex flex-wrap gap-1">
          {FILTERS.map((f) => (
            <button
              key={f.value}
              type="button"
              onClick={() => setStatus(f.value)}
              aria-pressed={status === f.value}
              className={
                status === f.value
                  ? "rounded-lg bg-accent-wash px-2.5 py-1 text-xs font-medium text-accent"
                  : "rounded-lg px-2.5 py-1 text-xs font-medium text-ink-dim hover:text-ink"
              }
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <ListSkeleton />
      ) : error ? (
        <ListError message={error} onRetry={onRetry} />
      ) : rows.length === 0 ? (
        <ListEmpty status={status} />
      ) : (
        <ul className="divide-y divide-line">
          {rows.map((f) => {
            // Include region + type: a resource_id can repeat across regions or
            // resource types, and a duplicate key would expand the wrong row.
            const key = `${f.check_id}:${f.region}:${f.resource_type}:${f.resource_id}`;
            return (
              <FindingRow
                key={key}
                finding={f}
                open={openKey === key}
                onToggle={() => setOpenKey(openKey === key ? null : key)}
              />
            );
          })}
        </ul>
      )}
    </section>
  );
}

function FindingRow({
  finding,
  open,
  onToggle,
}: {
  finding: Finding;
  open: boolean;
  onToggle: () => void;
}) {
  return (
    <li className={`border-l-4 ${SEV_STRIPE[finding.severity]}`}>
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        className="flex w-full items-center gap-4 px-5 py-3 text-left hover:bg-surface-base"
      >
        <span className="w-24 shrink-0">
          <SeverityBadge severity={finding.severity} />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-medium text-ink">{finding.title}</span>
          <span className="block truncate font-mono text-xs text-ink-dim">
            {finding.resource_id}
          </span>
        </span>
        <code className="hidden shrink-0 rounded border border-line px-2 py-0.5 font-mono text-xs text-ink-faint md:inline">
          {finding.check_id}
        </code>
        <StatusBadge status={finding.status} />
        <Chevron open={open} />
      </button>
      {open && <FindingDetail finding={finding} />}
    </li>
  );
}

function FindingDetail({ finding }: { finding: Finding }) {
  return (
    <div className="space-y-3 border-t border-line bg-surface-base px-5 py-4">
      <Field label="Detail">{finding.detail}</Field>
      <Field label="Remediation">{finding.remediation}</Field>
      <Field label="Resource ARN">
        <code className="break-all font-mono text-xs text-ink-dim">
          {finding.resource_arn || "—"}
        </code>
      </Field>
      <Field label="Evidence">
        <pre className="overflow-x-auto rounded-lg border border-line bg-surface-panel p-3 font-mono text-xs text-ink-dim">
          {JSON.stringify(finding.evidence, null, 2)}
        </pre>
      </Field>
      <Field label="Region · Account · Checked">
        <span className="font-mono text-xs text-ink-dim">
          {finding.region} · {finding.account_id} · {new Date(finding.checked_at).toLocaleString()}
        </span>
      </Field>
      {finding.status === "NON_COMPLIANT" && <RemediationPanel finding={finding} />}
    </div>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <p className="font-mono text-xs uppercase tracking-wider text-ink-faint">{label}</p>
      <div className="mt-0.5 text-sm text-ink">{children}</div>
    </div>
  );
}

function Chevron({ open }: { open: boolean }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden
      className={
        open
          ? "shrink-0 rotate-180 text-ink-faint transition-transform motion-reduce:transition-none"
          : "shrink-0 text-ink-faint transition-transform motion-reduce:transition-none"
      }
    >
      <path
        d="m6 9 6 6 6-6"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function ListSkeleton() {
  return (
    <ul className="divide-y divide-line" aria-busy="true" aria-label="Loading findings">
      {[0, 1, 2].map((i) => (
        <li key={i} className="flex items-center gap-4 px-5 py-4">
          <div className="h-3 w-20 rounded bg-surface-base motion-safe:animate-pulse" />
          <div className="h-3 flex-1 rounded bg-surface-base motion-safe:animate-pulse" />
          <div className="h-5 w-24 rounded-full bg-surface-base motion-safe:animate-pulse" />
        </li>
      ))}
    </ul>
  );
}

function ListError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="px-5 py-8 text-center">
      <p className="text-ink">Couldn&apos;t load findings.</p>
      <p className="mt-1 text-sm text-ink-dim">{message}</p>
      <button
        type="button"
        onClick={onRetry}
        className="mt-4 rounded-lg border border-line bg-surface-base px-3 py-1.5 text-sm font-medium text-ink hover:border-line-strong"
      >
        Retry
      </button>
    </div>
  );
}

function ListEmpty({ status }: { status: StatusFilter }) {
  const msg =
    status === "NON_COMPLIANT"
      ? "No outstanding violations — every evaluated resource is compliant."
      : status === "ALL"
        ? "No resources have been evaluated yet."
        : `No ${status.toLowerCase().replace("_", " ")} findings.`;
  return (
    <div className="px-5 py-10 text-center">
      <p className="text-ink">{msg}</p>
      <p className="mt-1 text-sm text-ink-dim">
        Findings appear here after a detective scan of the account.
      </p>
    </div>
  );
}
