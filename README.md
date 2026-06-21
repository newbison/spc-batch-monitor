<p align="right">
  <b>English</b> · <a href="README_CN.md">中文</a>
</p>

<p align="center">
  <a href="https://spc-batch-monito-tgnpmprhsqmpuxr4q6wktu.streamlit.app/"><img src="https://img.shields.io/badge/Live_Demo-Streamlit-00BFA5?style=for-the-badge&logo=streamlit&logoColor=white" alt="Live Demo"></a>
  <a href="https://github.com/newbison/spc-batch-monitor"><img src="https://img.shields.io/badge/GitHub-Open_Source-181717?style=for-the-badge&logo=github&logoColor=white" alt="GitHub"></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" alt="Streamlit">
  <img src="https://img.shields.io/badge/Plotly-3F4F75?style=for-the-badge&logo=plotly&logoColor=white" alt="Plotly">
  <img src="https://img.shields.io/badge/NumPy-013243?style=for-the-badge&logo=numpy&logoColor=white" alt="NumPy">
  <img src="https://img.shields.io/badge/SciPy-8CAAE6?style=for-the-badge&logo=scipy&logoColor=white" alt="SciPy">
  <img src="https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite">
  <img src="https://img.shields.io/badge/Pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white" alt="Pytest">
</p>

<h1 align="center">🔥 FORGE AI — SPC Platform</h1>
<h3 align="center">Statistical Process Control & Design of Experiments</h3>
<h4 align="center" style="color:#8895A8;font-weight:400">
  Turn batch data into process intelligence. From control charts to DOE optimization — all in one platform.
</h4>

<p align="center">
  <b>Upload your data → see control limits and violations → analyze capability → design experiments → optimize</b><br>
  X-bar & R charts · Western Electric rules · Capability analysis · Screening & full factorial designs · RSM · Desirability optimization
</p>

---

![App screenshot](image/README/1778922140812.png)

---

## What Is This?

Whether you are a **process engineer** monitoring production quality, an **R&D scientist** optimizing a formulation, or a **quality manager** tracking KPIs — the challenge is the same:

> *You need to know if your process is in control, capable, and where to focus improvement — without jumping between six different tools.*

A production engineer spends hours making X-bar and R charts in Excel. An R&D scientist runs a one-factor-at-a-time experiment because DOE software is too expensive or too complex. A quality manager pulls data from three systems to get one dashboard view.

**FORGE AI — SPC Platform fixes this. One tool for monitoring, analysis, and optimization.**

```
  ┌─────────────┐     ┌──────────────────┐     ┌──────────────────┐     ┌───────────────┐
  │             │     │                  │     │                  │     │               │
  │   Upload    │ ──▶ │  SPC Analysis    │ ──▶ │  DOE Design &    │ ──▶ │  Manager      │
  │   Batch     │     │  · Control charts │     │  Analysis        │     │  Dashboard    │
  │   Data      │     │  · Capability     │     │  · Factorial     │     │  · KPIs       │
  │             │     │  · Rules checks   │     │  · RSM / Surface │     │  · Trends     │
  └─────────────┘     └──────────────────┘     └──────────────────┘     └───────────────┘
```

---

## Features

### Multi-Role Platform

| Role | Access | What You Can Do |
|------|--------|-----------------|
| 👨‍🔬 **Operator** | Data Entry | Upload CSVs, manual entry, view/edit today's batches |
| 🔧 **Engineer** | SPC + DOE | Control charts, capability, DOE wizard (define→design→capture→analyze→optimize) |
| 📊 **Manager** | Dashboard | KPI cards, status table (🟢/🟡/🔴/⚪), trend analysis |
| ⚙️ **Admin** | Data Management | Filter, edit, delete, export, import — full CRUD |

### SPC — Statistical Process Control

- **X-bar & R control charts** with dynamic subgroup sizes (n=2–25) and ASTM E2587 constants
- **Western Electric Rules** — Rule 1 (beyond 3σ), Rule 2 (2 of 3 beyond 2σ), Rule 4 (8 consecutive same side), trending (6 up/down)
- **Trend analysis** — run chart, moving range chart, rolling Ppk with sliding window
- **Process capability** — Pp, Ppk, PPM with histogram and spec lines (one-sided specs via NaN)
- **Batch-to-batch boxplots** with spec line overlays
- **PPTX report export** — auto-generated SPC reports with charts and narrative summaries

### DOE — Design of Experiments

- **Full & fractional factorial designs** — 2^k full factorial, 2^(k-p) fractional factorial (Resolution IV/V), Box-Behnken RSM
- **No external DOE library** — self-contained factorial generators in pure NumPy
- **Regression analysis** — linear models with main effects + 2-way interactions, plus RSM quadratic models (statsmodels)
- **Curvature detection** — two-sample t-test comparing center-point vs. factorial-point responses
- **Visualization** — main effects plots, Pareto of effects, contour plots, 3D response surfaces
- **Derringer-Suich desirability** — multi-response optimization with prediction intervals and multi-start scipy optimization
- **Session persistence** — save, resume, and iterate across sessions

---

## Quick Start

```bash
git clone https://github.com/newbison/spc-batch-monitor.git
cd spc-batch-monitor
pip install -r requirements.txt
streamlit run app.py
```

That's it. Sample data auto-loads on first launch. Select an app (SPC or DOE) from the sidebar, then choose your role from the top bar.

No external DOE library required — the factorial generators are self-contained and work on Python 3.9+.

---

## Monitored Parameters

| Parameter | Replicates | LSL | USL | Units |
|-----------|-----------|-----|-----|-------|
| Viscosity | 5 | 0.6 | 1.5 | N/mm |
| Density | 15 | 1000.0 | — | — |
| Hardness | 8 | 10.0 | 50.0 | mm |
| Elasticity | 10 | 5.0 | 20.0 | g/inch |

Variable subgroup sizes (5–15) auto-detected by counting non-NaN replicates per row.

---

## Architecture

```
app.py (Hub shell)
 ├── SPC sub-app
 │   ├── Role bar + Sidebar (formula/param selection)
 │   ├── UI (Streamlit pages by role)
 │   │   └─> Visualization (Plotly chart builders)
 │   │        └─> SPC Engine (pure Python — no framework deps)
 │   │             └─> Data Access (repository pattern → SQLite)
 │   │                  └─> Validation (row-level guard before writes)
 │   └── Reports (python-pptx + Kaleido)
 │
 └── DOE sub-app
     ├── _factorial.py  — self-contained fullfact, fracfact, bbdesign
     ├── designs.py      — factorial + Box-Behnken design matrices
     ├── analysis.py     — linear + RSM regression (statsmodels)
     ├── optimization.py — Derringer-Suich desirability (scipy)
     └── persistence.py  — SQLite session CRUD (JSON columns)
```

All engines are **framework-agnostic** — they take DataFrames or arrays and return plain dicts. The repository pattern abstracts storage so SQLite can be swapped for PostgreSQL without touching UI or business logic.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **UI** | Streamlit |
| **Charts** | Plotly |
| **SPC Engine** | Pure Python (NumPy/SciPy) |
| **DOE Engine** | NumPy, statsmodels, scipy.optimize |
| **Reports** | python-pptx, Kaleido |
| **Database** | SQLite (WAL mode, repository pattern) |
| **Testing** | Pytest (90+ tests) |

---

## Testing

```bash
pytest tests/ -v
```

90+ tests covering:
- Control limits (X-bar & R with dynamic n)
- Western Electric rules (1, 2, 4, trending)
- Capability calculations (Pp, Ppk, PPM, one-sided specs)
- Data validation (rejects bad rows before write)
- SQLite repository operations (CRUD, dedup, auto-migration)
- End-to-end integration (SPC pipeline)
- DOE design generation (full factorial, fractional factorial, Box-Behnken)
- DOE regression analysis (linear, RSM, overparameterization guard)
- DOE desirability optimization (RMSE-based prediction intervals)
- DOE persistence (JSON columns, whitelist validation)
