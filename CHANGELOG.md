# Changelog

## 2026-05-16

- SQLite data storage (SqliteRepository) replacing single-file CSV as source of truth
- Data validation module: rejects negative values, bad dates, non-numeric data
- Deduplication via UNIQUE(batch_id, formula, parameter); CSV upload reports inserted/skipped/errors
- Auto-migration: existing coating_batches.csv imported into SQLite on first run
- Variable subgroup size support (adhesion=5, cohesion=15, rolling_ball_tack=8, liner_release=10)
- New visualization modules: run chart, moving range, rolling Ppk, boxplot
- Shared Plotly theme (_theme.py) and Streamlit visual overhaul (CSS + config.toml)
- Engineer page: 4 chart tabs, all-formulas out-of-spec warning banner, side-by-side selectors
- Manager dashboard: warning banners for out-of-spec and marginal items at top
- Updated specs: adhesion 0.6-1.5 N/mm, cohesion >=1000, liner_release 5-20, rolling_ball_tack 10-50
- Regenerated sample data with correct specs, variable reps, renamed parameter
- 31 tests passing (19 new: validation, SqliteRepository, SQLite integration)
