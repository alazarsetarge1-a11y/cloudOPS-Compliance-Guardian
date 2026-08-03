// Adds jest-dom matchers (toBeInTheDocument, etc.) to Vitest's expect, and
// unmounts rendered components between tests (we don't use Vitest globals).
import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => cleanup());
