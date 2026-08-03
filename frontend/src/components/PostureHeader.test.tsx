import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { ComplianceScore } from "../types";
import { PostureHeader } from "./PostureHeader";

const score = (over: Partial<ComplianceScore> = {}): ComplianceScore => ({
  total_findings: 3,
  by_status: { COMPLIANT: 2, NON_COMPLIANT: 1, ERROR: 0 },
  non_compliant_by_severity: { CRITICAL: 0, HIGH: 1, MEDIUM: 0, LOW: 0 },
  compliance_score_pct: 66.7,
  ...over,
});

describe("PostureHeader", () => {
  it("renders a loading skeleton", () => {
    render(<PostureHeader score={null} loading error={null} onRetry={() => {}} />);
    expect(screen.getByLabelText(/loading compliance posture/i)).toBeInTheDocument();
  });

  it("renders an error with a working retry", () => {
    const onRetry = vi.fn();
    render(<PostureHeader score={null} loading={false} error="503 — down" onRetry={onRetry} />);
    expect(screen.getByText("503 — down")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /retry/i }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("renders the empty state when nothing is evaluated", () => {
    render(
      <PostureHeader
        score={score({ total_findings: 0 })}
        loading={false}
        error={null}
        onRetry={() => {}}
      />,
    );
    expect(screen.getByText(/no resources have been evaluated/i)).toBeInTheDocument();
  });

  it("flags action needed when critical/high are present", () => {
    render(<PostureHeader score={score()} loading={false} error={null} onRetry={() => {}} />);
    expect(screen.getByText(/action needed/i)).toBeInTheDocument();
    expect(screen.getByText(/2 of 3 resources compliant/i)).toBeInTheDocument();
  });

  it("shows all clear when no critical/high", () => {
    const clear = score({ non_compliant_by_severity: { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 } });
    render(<PostureHeader score={clear} loading={false} error={null} onRetry={() => {}} />);
    expect(screen.getByText(/all clear/i)).toBeInTheDocument();
  });

  it("shows scan-incomplete (not all clear) when checks errored", () => {
    const withErrors = score({
      by_status: { COMPLIANT: 2, NON_COMPLIANT: 0, ERROR: 1 },
      non_compliant_by_severity: { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 },
    });
    render(<PostureHeader score={withErrors} loading={false} error={null} onRetry={() => {}} />);
    expect(screen.getByText(/scan incomplete/i)).toBeInTheDocument();
    expect(screen.queryByText(/all clear/i)).not.toBeInTheDocument();
  });

  it("suppresses the % when no control is evaluable", () => {
    const allError = score({
      by_status: { COMPLIANT: 0, NON_COMPLIANT: 0, ERROR: 2 },
      non_compliant_by_severity: { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 },
      compliance_score_pct: null,
    });
    render(<PostureHeader score={allError} loading={false} error={null} onRetry={() => {}} />);
    expect(screen.getByText("n/a")).toBeInTheDocument();
    expect(screen.queryByText("%")).not.toBeInTheDocument();
  });

  it("suppresses the % on a partial scan (some evaluable + some errored)", () => {
    const partial = score({
      by_status: { COMPLIANT: 2, NON_COMPLIANT: 1, ERROR: 1 },
      non_compliant_by_severity: { CRITICAL: 0, HIGH: 1, MEDIUM: 0, LOW: 0 },
      compliance_score_pct: 66.7,
    });
    render(<PostureHeader score={partial} loading={false} error={null} onRetry={() => {}} />);
    expect(screen.getByText("n/a")).toBeInTheDocument();
    expect(screen.queryByText("%")).not.toBeInTheDocument();
  });
});
