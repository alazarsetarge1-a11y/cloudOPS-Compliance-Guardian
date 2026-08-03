/** API response shapes — mirror the backend's Pydantic models (the contract). */

export type Status = "COMPLIANT" | "NON_COMPLIANT" | "ERROR";
export type Severity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

export const SEVERITY_ORDER: Severity[] = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];

export interface Finding {
  check_id: string;
  resource_id: string;
  resource_arn: string;
  resource_type: string;
  region: string;
  account_id: string;
  status: Status;
  severity: Severity;
  title: string;
  detail: string;
  remediation: string;
  evidence: Record<string, unknown>;
  checked_at: string;
}

export interface ComplianceScore {
  total_findings: number;
  by_status: Record<Status, number>;
  non_compliant_by_severity: Record<Severity, number>;
  /** null when there are no evaluable resources — distinct from 0%. */
  compliance_score_pct: number | null;
}
