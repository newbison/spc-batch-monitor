# PPTX Report Export — Design Spec

**Date:** 2026-06-14
**Status:** Approved
**Scope:** On-demand PowerPoint report generation for SPC Batch Monitor

---

## Problem

The SPC Batch Monitor app has rich charts, capability metrics, and violation detection — but nothing leaves the app. Reports exist only as live Streamlit pages. Engineers and managers need to export analysis as PowerPoint files for management reviews, customer presentations, and shift handoffs.

## Decisions

| Decision | Choice |
|----------|--------|
| Approach | A — single fixed 5-slide template |
| Output format | .pptx only (PDF/Excel deferred) |
| Trigger | On-demand button click |
| Audience | Engineer, Manager, Admin (not Operator) |
| PPTX library | `python-pptx` (pure Python, no Node.js) |
| Chart rendering | Existing Plotly builders → kaleido PNG → embed in slides |
| UI location | Second tab inside Engineer page (shared formula/param selection) |
| Style | Corporate Professional — navy title, white body, steel-blue accent |

## Architecture

### New files

| File | Purpose |
|------|---------|
| `reports/__init__.py` | Package marker |
| `reports/pptx_generator.py` | Pure Python: takes DataFrame + config → returns `.pptx` as `BytesIO`. No Streamlit imports. |
| `reports/narrative.py` | Pure Python: takes limits/capability/violations → returns plain-text strings for executive summary. |

### Modified files

| File | Change |
|------|--------|
| `ui/engineer/chart_view.py` | Add second tab "📥 Export Report" with filter bar + generate button + download link |
| `ui/manager/dashboard.py` | Add a small "Export this analysis" button (stretch — optional) |
| `requirements.txt` | Add `python-pptx` and `kaleido` |

### No changes to

- `visualization/` — reuse existing `build_*()` functions as-is
- `spc_engine/` — reuse existing `compute_xbar_r`, `check_rules`, `compute_capability`
- `data_access/` — reuse existing repository methods

### Data flow

```
User clicks "Generate"
  → chart_view.py collects formula/param/date-range from session state
  → calls repo.get_for_parameter() to get filtered DataFrame
  → calls spc_engine (compute_xbar_r, check_rules, compute_capability)
  → calls narrative.build_summary() for executive summary text
  → calls visualization.build_*() for Plotly Figures
  → renders each Figure to PNG BytesIO via kaleido
  → calls pptx_generator.build_report(figs, text, metadata) → BytesIO
  → st.download_button() serves the .pptx file
```

## PPTX Slide Template (5 slides)

### Slide 1 — Title

- **Background:** Navy (#1E3A5F) full bleed
- **Content (centered):**
  - "SPC Process Report"
  - "Formula: {formula} / Parameter: {parameter}"
  - Date range + generated timestamp (smaller, white-muted)

### Slide 2 — Executive Summary

- **Background:** White
- **Layout:** Left-aligned text block, 2–3 short paragraphs
- **Content (auto-generated):**
  - Capability verdict: "Process is capable (Ppk = 1.52)" or "Process is marginal — requires attention (Ppk = 1.08)"
  - Key metrics: N batches, Pp, Ppk, total PPM, # OOC events
  - Trend note: "No significant trend detected" or "Downward trend in last 8 batches"
  - Action items (if OOC): "3 out-of-control events detected between Mar 12–18"

### Slide 3 — X-bar & R Control Chart

- **Background:** White
- **Layout:** Full-width chart image (Plotly → PNG, ~12" × 6")
- **Caption below image:** "Control limits frozen from first {baseline_n} batches"

### Slide 4 — Capability Analysis

- **Background:** White
- **Layout:** Two-column — left: histogram image, right: KPI table
- **Left:** `build_capability_chart()` rendered to PNG
- **Right:** Formatted table with Pp, Ppk, Mean, σ, PPM, Batch count

### Slide 5 — Trend Analysis

- **Background:** White
- **Layout:** Full-width chart image — `build_rolling_ppk_chart()`
- **Caption:** Rolling Ppk (window=10)

## Streamlit UI

- **Location:** Second tab inside the Engineer view (tab 1 = existing "SPC Analysis", tab 2 = "📥 Export Report")
- **Shared state:** Formula/parameter selection carries over from tab 1 via `st.session_state`
- **Controls:** Date range pickers (default: last 90 days)
- **Action:** "Generate PowerPoint" button
- **Output:** Preview summary (batches, Ppk status) + `st.download_button` for the .pptx file
- **Roles:** Engineer, Manager, Admin

## Narrative Generator Logic (`reports/narrative.py`)

`build_summary(cap, violations, limits, formula, parameter, date_range, n_batches)` returns a dict with:

- `verdict`: one-line capability assessment string
- `metrics_bullet`: "Pp = X, Ppk = Y, N = Z batches, PPM = W"
- `trend_note`: assessment of rolling Ppk direction (improving/stable/declining)
- `ooc_summary`: count and date range of OOC events, or "No out-of-control events detected"
- `action_items`: suggested next steps (empty if process is capable)

## Design Style

- **Color palette:** Navy #1E3A5F (title bg), White #FFFFFF (body bg), Steel Blue #4A90D9 (accent), Dark Gray #333333 (body text)
- **Typography:** Calibri (title 36pt, section 20pt, body 14pt, caption 10pt)
- **Spacing:** 0.5" margins, 0.3" between content blocks
- **Chart image resolution:** kaleido scale=2 for print quality

## Out of Scope (deferred)

- PDF export (can add later using same reports/ module)
- Excel export (different data shape — not just charts)
- Scheduled/automated report generation
- Per-audience template variants
- User-configurable slide composition
- Company logo / branding customization
