---
name: dashboard-design-system
description: Design rules and component conventions for the Cloud Compliance Guardian React dashboard. Use when working in frontend/, building or reviewing any UI component, choosing colors or spacing, laying out a page, or designing the findings view, IAM risk heatmap, or remediation timeline. Use before writing any Tailwind class.
---

# Dashboard design system

## The bar

This dashboard is the first thing a recruiter looks at. It must not read as a
default admin template. The test: *does this look like a product someone chose
to build, or like a Bootstrap page with data poured into it?*

Concretely that means: no unstyled `<table>` grids as the primary view, no
default blue/red/green traffic lights, no evenly-weighted wall of cards where
everything competes for attention.

## Non-negotiable: tokens, not literals

Every color, spacing value, radius, and font size comes from a token defined
once in the Tailwind theme. **A raw `text-[#e11d48]` or `p-[13px]` in a
component is a defect**, not a style preference — CodeRabbit is configured to
flag it.

Define semantic tokens, not palette names. `bg-severity-critical` survives a
redesign; `bg-red-600` does not.

```js
// tailwind.config.js — semantic layer over the raw palette
severity: {
  critical: 'var(--sev-critical)',
  high:     'var(--sev-high)',
  medium:   'var(--sev-medium)',
  low:      'var(--sev-low)',
}
```

Drive the values from CSS custom properties on `:root` so dark mode is a
variable swap, not a second set of classes on every element.

## Charts

**Load the `dataviz` skill before writing any chart, meter, stat tile, or KPI
row.** It owns the color formula, the form heuristic, and the accessibility
rules. Do not improvise chart colors here — the severity tokens above are for
UI chrome and badges; chart series colors follow `dataviz`.

Two project-specific constraints on top of it:

- **Severity color must never be the only signal.** Pair it with a shape, an
  icon, or a text label. Roughly 1 in 12 men has a color vision deficiency, and
  red/green severity coding is exactly the failure case. For a *security*
  portfolio project, getting this wrong is a bad look on its own terms.
- **Every chart needs a text alternative** — a caption or accessible summary
  stating the takeaway. "23 findings, 4 critical, up 2 since last scan" is more
  useful than the chart to a screen reader and to a skimming recruiter.

## Visual hierarchy — decide what matters

The page must answer, in this order, without scrolling:

1. **Is anything on fire right now?** Critical/high count, and whether it is
   trending up. One dominant element.
2. **Is the system working?** Findings auto-remediated vs. outstanding. This is
   the project's whole thesis — that it corrects, not just reports. Make it
   visible, not buried in a tab.
3. **What specifically is wrong?** The findings list. Dense, scannable,
   filterable — this is where a table is correct, but a *designed* table:
   deliberate column weights, tabular numerals, severity as a leading visual
   anchor, row hover affordance.

Everything else (heatmap detail, full remediation history) is a second screen.
Resist putting five equally-sized cards in a row; that communicates that nothing
is more important than anything else.

## The three signature views

- **Findings list** — the workhorse. Sort by severity then age. Group by
  `check_id` or by account. Row expands to show the `evidence` payload; that
  detail is what makes it read as a real compliance tool rather than a mockup.
- **IAM risk heatmap** — principals on one axis, risk dimensions on the other
  (privilege breadth, MFA, key age, last used). Use a **sequential** scale, not
  a categorical one — this is magnitude data. Cells need tooltips and keyboard
  focus, not hover-only reveal.
- **Remediation timeline** — the differentiator. Show finding detected →
  runbook triggered → resolved, with real durations. This is the visual proof
  of the Preventive/Detective/Corrective thesis. Give it room.

## Component conventions

- Function components, TypeScript, named exports.
- Presentational components take data as props and do not fetch. Data fetching
  lives in hooks (`useFindings`, `useRemediations`) so the components stay
  testable and Storybook-able.
- **Every data view implements four states**: loading (skeleton, not a spinner
  in an empty page), empty (with a sentence explaining what would populate it),
  error (with what failed and a retry), and loaded. A view missing the empty
  state looks broken on first run — which is exactly when a recruiter sees it.
- Findings data contains attacker-influenceable strings (bucket names, ARNs,
  tag values). Render as text. Never `dangerouslySetInnerHTML`.

## Accessibility floor

Not optional on a security portfolio piece.

- Interactive elements are real `<button>`/`<a>`, reachable by Tab, with a
  visible focus ring.
- Contrast ≥ 4.5:1 for body text, ≥ 3:1 for large text and meaningful graphics.
- Charts and heatmaps expose their data to assistive tech.
- Respect `prefers-reduced-motion` on any transition or animated chart entry.
