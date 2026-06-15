# Changelog

## 2026-06-15

- **DOE (Design of Experiments) page** — full wizard workflow for Engineer role
  - `doe/designs.py`: full factorial, fractional factorial (2^(k-p) Resolution IV), Box-Behnken design generation via pyDOE2, with center points and coded ↔ real unit conversion
  - `doe/analysis.py`: OLS linear regression + RSM second-order model via statsmodels, ANOVA, Pareto chart data, curvature test (factorial vs center-point comparison)
  - `doe/optimization.py`: Derringer-Suich desirability function (nominal/larger/smaller-the-best), geometric mean overall desirability, scipy.optimize multi-start L-BFGS-B optimization with response bounds
  - `doe/persistence.py`: SQLite CRUD for DOE sessions with JSON columns (factors, responses, design matrix, analysis results)
  - `ui/engineer/doe_view.py`: Streamlit wizard — Landing, Define Factors & Responses, Generate Design Matrix, Capture Results, Analyze (regression summary, main effects, Pareto, contour/surface plots), Optimize (desirability settings, multi-start search, optimal conditions)
  - Sidebar: Engineer role now has SPC Analysis + DOE page selector
  - Promote-to-full-factorial bridge for fractional designs
  - 24 new tests (7 designs + 6 analysis + 6 optimization + 5 persistence), all 73 tests passing
- Patched pyDOE2 `import imp` → `import importlib` for Python 3.12+ compatibility
- Extended SPC constants table (n=2..25) in config.py

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
