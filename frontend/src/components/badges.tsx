import type { Severity, Status } from "../types";

/**
 * Severity + status badges. The class strings are written out in FULL in these
 * maps (not built by interpolation) because Tailwind extracts classes by static
 * source scanning — `bg-severity-${x}` would never be generated.
 */

const SEV: Record<Severity, { label: string; dot: string; text: string }> = {
  CRITICAL: { label: "Critical", dot: "bg-severity-critical", text: "text-severity-critical" },
  HIGH: { label: "High", dot: "bg-severity-high", text: "text-severity-high" },
  MEDIUM: { label: "Medium", dot: "bg-severity-medium", text: "text-severity-medium" },
  LOW: { label: "Low", dot: "bg-severity-low", text: "text-severity-low" },
};

export function SeverityBadge({ severity }: { severity: Severity }) {
  const s = SEV[severity];
  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-medium">
      {/* shape marker so severity is never encoded by color alone */}
      <span aria-hidden className={`h-2 w-2 rounded-full ${s.dot}`} />
      <span className={s.text}>{s.label}</span>
    </span>
  );
}

const STATUS: Record<Status, { label: string; dot: string; text: string }> = {
  NON_COMPLIANT: {
    label: "Non-compliant",
    dot: "bg-status-noncompliant",
    text: "text-status-noncompliant",
  },
  COMPLIANT: { label: "Compliant", dot: "bg-status-compliant", text: "text-status-compliant" },
  ERROR: { label: "Error", dot: "bg-status-error", text: "text-status-error" },
};

export function StatusBadge({ status }: { status: Status }) {
  const s = STATUS[status];
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-line px-2 py-0.5 text-xs">
      <span aria-hidden className={`h-1.5 w-1.5 rounded-full ${s.dot}`} />
      <span className={s.text}>{s.label}</span>
    </span>
  );
}
