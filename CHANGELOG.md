# Changelog

## 2026-05-15

- Initial MVP: Streamlit SPC app for adhesive batch process monitoring
- Data access layer with CSV repository (formula + inline spec columns)
- SPC engine: X-bar & R control limits, Western Electric rules, Pp/Ppk/PPM capability
- Plotly visualizations: control charts (paired X-bar/R), capability histograms
- Operator UI: CSV upload (default) with validation + manual entry with formula/spec toggles
- Engineer UI: combined formula-scoped SPC analysis (chart + capability on one page)
- Manager dashboard: formula count, today's uploads, red/yellow/green status per formula×parameter
- One-sided spec support (NaN = no limit)
- 12 tests passing (control limits, rules, capability, integration)
- 30 batches sample data with 2 formulas (Adhesive A, Adhesive B)
