/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  // Dark mode is driven by CSS custom properties (see index.css), so it's a
  // variable swap under prefers-color-scheme — not a second set of classes.
  darkMode: "media",
  theme: {
    extend: {
      // SEMANTIC tokens only — names describe meaning, not palette. Every value
      // resolves to a CSS variable, so a redesign edits index.css, not components.
      colors: {
        surface: {
          base: "var(--surface-base)",
          panel: "var(--surface-panel)",
          raised: "var(--surface-raised)",
        },
        line: {
          DEFAULT: "var(--line)",
          strong: "var(--line-strong)",
        },
        ink: {
          DEFAULT: "var(--ink)",
          dim: "var(--ink-dim)",
          faint: "var(--ink-faint)",
        },
        accent: {
          DEFAULT: "var(--accent)",
          wash: "var(--accent-wash)",
        },
        severity: {
          critical: "var(--sev-critical)",
          high: "var(--sev-high)",
          medium: "var(--sev-medium)",
          low: "var(--sev-low)",
        },
        status: {
          compliant: "var(--status-compliant)",
          noncompliant: "var(--status-noncompliant)",
          error: "var(--status-error)",
        },
      },
      fontFamily: {
        sans: [
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "'Segoe UI'",
          "Roboto",
          "Helvetica",
          "Arial",
          "sans-serif",
        ],
        mono: ["ui-monospace", "'SF Mono'", "'JetBrains Mono'", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};
