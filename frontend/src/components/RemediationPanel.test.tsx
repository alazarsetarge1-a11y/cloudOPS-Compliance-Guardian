import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

// Mock the API client so no real request goes out.
vi.mock("../lib/api", () => ({
  apiPost: vi.fn(),
  ApiError: class ApiError extends Error {
    status = 0;
  },
}));

import { apiPost } from "../lib/api";
import type { Finding, RemediationResult } from "../types";
import { RemediationPanel } from "./RemediationPanel";

const finding: Finding = {
  check_id: "s3-public-access",
  resource_id: "b1",
  resource_arn: "arn:aws:s3:::b1",
  resource_type: "AWS::S3::Bucket",
  region: "global",
  account_id: "123456789012",
  status: "NON_COMPLIANT",
  severity: "HIGH",
  title: "t",
  detail: "d",
  remediation: "r",
  evidence: {},
  checked_at: "2026-01-01T00:00:00Z",
};

const preview: RemediationResult = {
  check_id: "s3-public-access",
  resource_id: "b1",
  action: "AUTO_REMEDIATE",
  outcome: "PLANNED",
  summary: "Would re-enable Block Public Access on b1.",
  plan: {},
  executed_at: "2026-01-01T00:00:00Z",
};
const started: RemediationResult = {
  ...preview,
  outcome: "STARTED",
  summary: "Started SSM runbook on b1 (execution abc).",
};

const mockPost = vi.mocked(apiPost);

describe("RemediationPanel", () => {
  beforeEach(() => mockPost.mockReset());

  it("previews (dry run) then applies", async () => {
    mockPost.mockResolvedValueOnce(preview).mockResolvedValueOnce(started);
    render(<RemediationPanel finding={finding} />);

    fireEvent.click(screen.getByRole("button", { name: /preview remediation/i }));
    expect(await screen.findByText(/would re-enable block public access/i)).toBeInTheDocument();
    expect(mockPost).toHaveBeenCalledWith("/remediations", {
      check_id: "s3-public-access",
      resource_id: "b1",
      apply: false,
    });

    fireEvent.click(screen.getByRole("button", { name: /apply fix/i }));
    expect(await screen.findByText(/remediation started/i)).toBeInTheDocument();
    expect(mockPost).toHaveBeenLastCalledWith("/remediations", {
      check_id: "s3-public-access",
      resource_id: "b1",
      apply: true,
    });
  });
});
