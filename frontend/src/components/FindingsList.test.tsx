import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { Finding } from "../types";
import { FindingsList } from "./FindingsList";

const f = (over: Partial<Finding>): Finding => ({
  check_id: "s3-public-access",
  resource_id: "b1",
  resource_arn: "arn:aws:s3:::b1",
  resource_type: "AWS::S3::Bucket",
  region: "global",
  account_id: "123456789012",
  status: "NON_COMPLIANT",
  severity: "HIGH",
  title: "Public bucket",
  detail: "Block Public Access disabled",
  remediation: "Re-enable BPA",
  evidence: { public_access_block: false },
  checked_at: "2026-01-01T00:00:00Z",
  ...over,
});

const findings: Finding[] = [
  f({ resource_id: "bad-bucket" }),
  f({ check_id: "iam-mfa", resource_id: "ok-user", status: "COMPLIANT", severity: "LOW" }),
];

const props = { loading: false, error: null, onRetry: () => {} };

describe("FindingsList", () => {
  it("defaults to non-compliant findings only", () => {
    render(<FindingsList findings={findings} {...props} />);
    expect(screen.getByText("bad-bucket")).toBeInTheDocument();
    expect(screen.queryByText("ok-user")).not.toBeInTheDocument();
  });

  it("shows all findings when the All filter is selected", () => {
    render(<FindingsList findings={findings} {...props} />);
    fireEvent.click(screen.getByRole("button", { name: "All" }));
    expect(screen.getByText("bad-bucket")).toBeInTheDocument();
    expect(screen.getByText("ok-user")).toBeInTheDocument();
  });

  it("expands a row to reveal detail + evidence", () => {
    render(<FindingsList findings={[f({ resource_id: "bad-bucket" })]} {...props} />);
    expect(screen.queryByText(/Block Public Access disabled/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { expanded: false }));
    expect(screen.getByText(/Block Public Access disabled/)).toBeInTheDocument();
    expect(screen.getByText(/public_access_block/)).toBeInTheDocument();
  });

  it("shows the empty state when a filter matches nothing", () => {
    render(<FindingsList findings={[f({ status: "COMPLIANT" })]} {...props} />);
    expect(screen.getByText(/no outstanding violations/i)).toBeInTheDocument();
  });
});
