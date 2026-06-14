# PPTX Report Export — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an "Export Report" tab to the Engineer page that generates a 5-slide PowerPoint deck with SPC charts, capability metrics, and an auto-generated executive summary.

**Architecture:** A pure-Python `reports/` module (no Streamlit imports) produces `.pptx` bytes from Plotly chart images and SPC data. A new tab inside the existing Engineer `chart_view.py` provides the generate/download UI. Existing `visualization/` builders and `spc_engine/` functions are called directly — no modifications to those modules.

**Tech Stack:** `python-pptx` for PPTX creation, `kaleido` for Plotly→PNG rendering, existing `plotly` + `spc_engine`.

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `reports/__init__.py` | Create | Package marker |
| `reports/narrative.py` | Create | Auto-generate executive summary text from SPC data |
| `reports/pptx_generator.py` | Create | Build 5-slide PPTX from chart images + narrative + metadata |
| `ui/engineer/chart_view.py` | Modify | Add second tab "Export Report" with generate button + download |
| `tests/test_narrative.py` | Create | Tests for narrative generation |
| `tests/test_pptx_generator.py` | Create | Tests for PPTX generation (structure, not pixel-perfect) |
| `requirements.txt` | Modify | Add `python-pptx` and `kaleido` |

---

### Task 1: Install dependencies

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add python-pptx and kaleido to requirements.txt**

Add these two lines to the end of `D:\coding_is_fun\SPC\requirements.txt`:

```
python-pptx>=0.6.23
kaleido>=0.2.1
```

- [ ] **Step 2: Install the packages**

Run: `pip install python-pptx kaleido`
Expected: Both packages install successfully.

- [ ] **Step 3: Verify kaleido can render a Plotly figure**

Run:
```python
python -c "import plotly.graph_objects as go; fig = go.Figure(); fig.add_trace(go.Scatter(x=[1,2], y=[1,2])); img = fig.to_image(format='png'); print(f'OK: {len(img)} bytes')"
```
Expected: Prints `OK: <N> bytes` with N > 0.

- [ ] **Step 4: Verify python-pptx can create a presentation**

Run:
```python
python -c "from pptx import Presentation; prs = Presentation(); prs.save('test.pptx'); import os; os.remove('test.pptx'); print('OK')"
```
Expected: Prints `OK`.

- [ ] **Step 5: Commit**

```bash
git add requirements.txt
git commit -m "chore: add python-pptx and kaleido dependencies for PPTX report export"
```

---

### Task 2: Create `reports/__init__.py` and `reports/narrative.py`

**Files:**
- Create: `reports/__init__.py`
- Create: `reports/narrative.py`
- Test: `tests/test_narrative.py`

- [ ] **Step 1: Write the failing test**

Create `D:\coding_is_fun\SPC\tests\test_narrative.py`:

```python
import math
import numpy as np
from reports.narrative import build_summary


def test_capable_process_no_violations():
    """Capable process with no OOC → positive summary."""
    cap = {"Pp": 1.8, "Ppk": 1.52, "sigma_overall": 0.93, "mean": 8.45,
           "total_ppm": 127}
    violations = []
    limits = {"xbar": np.array([8.3, 8.4, 8.5, 8.6, 8.5, 8.4, 8.3, 8.4]),
              "baseline_n": 5}
    result = build_summary(
        cap=cap, violations=violations, limits=limits,
        formula="Coating A", parameter="adhesion",
        date_range=("2025-01-01", "2025-03-15"), n_batches=40,
    )
    assert "1.52" in result["verdict"]
    assert "capable" in result["verdict"].lower()
    assert result["ooc_summary"] == "No out-of-control events detected."
    assert result["action_items"] == ""
    assert "40" in result["metrics_bullet"]


def test_marginal_process_with_violations():
    """Marginal process with OOC events → warning in summary."""
    cap = {"Pp": 1.1, "Ppk": 1.08, "sigma_overall": 1.2, "mean": 8.45,
           "total_ppm": 5500}
    violations = [
        {"batch_index": 12, "rule": 1, "description": "Point beyond 3σ"},
        {"batch_index": 18, "rule": 4, "description": "8 consecutive above CL"},
    ]
    batch_ids = [f"B-{i:03d}" for i in range(20)]
    dates = [f"2025-03-{(i % 28) + 1:02d}" for i in range(20)]
    limits = {"xbar": np.zeros(20), "baseline_n": 10}
    result = build_summary(
        cap=cap, violations=violations, limits=limits,
        formula="Coating A", parameter="adhesion",
        date_range=("2025-03-01", "2025-03-28"),
        n_batches=20, batch_ids=batch_ids, dates=dates,
    )
    assert "marginal" in result["verdict"].lower()
    assert "1.08" in result["verdict"]
    assert "2" in result["ooc_summary"]
    assert result["action_items"] != ""


def test_not_capable_process():
    """Ppk < 1.0 → not capable verdict."""
    cap = {"Pp": 0.7, "Ppk": 0.65, "sigma_overall": 2.0, "mean": 8.45,
           "total_ppm": 50000}
    violations = [
        {"batch_index": 5, "rule": 1, "description": "Point beyond 3σ"},
    ]
    batch_ids = [f"B-{i:03d}" for i in range(10)]
    dates = [f"2025-01-{(i % 28) + 1:02d}" for i in range(10)]
    limits = {"xbar": np.zeros(10), "baseline_n": 10}
    result = build_summary(
        cap=cap, violations=violations, limits=limits,
        formula="Coating A", parameter="adhesion",
        date_range=("2025-01-01", "2025-01-31"),
        n_batches=10, batch_ids=batch_ids, dates=dates,
    )
    assert "not capable" in result["verdict"].lower()
    assert "0.65" in result["verdict"]


def test_no_spec_limits():
    """No spec limits → Ppk is NaN → 'no specification' verdict."""
    cap = {"Pp": float("nan"), "Ppk": float("nan"), "sigma_overall": 0.5,
           "mean": 8.45, "total_ppm": 0}
    violations = []
    limits = {"xbar": np.zeros(5), "baseline_n": 5}
    result = build_summary(
        cap=cap, violations=violations, limits=limits,
        formula="Coating A", parameter="adhesion",
        date_range=("2025-01-01", "2025-01-31"), n_batches=5,
    )
    assert "no spec" in result["verdict"].lower() or "nan" in result["verdict"].lower()


def test_trend_detection():
    """Detect declining rolling Ppk trend."""
    # Simulate declining xbar values
    cap = {"Pp": 1.3, "Ppk": 1.05, "sigma_overall": 1.0, "mean": 8.0,
           "total_ppm": 3000}
    violations = []
    xbar = np.array([8.5, 8.4, 8.3, 8.2, 8.1, 8.0, 7.9, 7.8, 7.7, 7.6,
                      7.5, 7.4, 7.3, 7.2, 7.1])
    limits = {"xbar": xbar, "baseline_n": 10}
    result = build_summary(
        cap=cap, violations=violations, limits=limits,
        formula="Coating A", parameter="adhesion",
        date_range=("2025-01-01", "2025-03-15"), n_batches=15,
    )
    # Should detect downward trend
    assert "declin" in result["trend_note"].lower() or "downward" in result["trend_note"].lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_narrative.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'reports'`

- [ ] **Step 3: Create the package init**

Create `D:\coding_is_fun\SPC\reports\__init__.py` (empty file).

- [ ] **Step 4: Implement narrative.py**

Create `D:\coding_is_fun\SPC\reports\narrative.py`:

```python
"""Auto-generated executive summary text for SPC reports."""

import math
import numpy as np


def build_summary(
    cap: dict,
    violations: list[dict],
    limits: dict,
    formula: str,
    parameter: str,
    date_range: tuple[str, str],
    n_batches: int,
    batch_ids: list[str] | None = None,
    dates: list[str] | None = None,
) -> dict:
    """Generate executive summary sections from SPC analysis results.

    Returns dict with keys: verdict, metrics_bullet, trend_note, ooc_summary, action_items.
    """
    ppk = cap["Ppk"]

    # --- Verdict ---
    if math.isnan(ppk):
        verdict = f"{formula} / {parameter}: no specification limits defined; capability cannot be assessed."
    elif ppk >= 1.33:
        verdict = f"{formula} / {parameter}: process is capable (Ppk = {ppk:.2f})."
    elif ppk >= 1.0:
        verdict = (f"{formula} / {parameter}: process is marginal — "
                   f"requires attention (Ppk = {ppk:.2f}).")
    else:
        verdict = (f"{formula} / {parameter}: process is NOT capable "
                   f"(Ppk = {ppk:.2f}). Corrective action recommended.")

    # --- Metrics bullet ---
    pp_str = f"{cap['Pp']:.2f}" if not math.isnan(cap["Pp"]) else "N/A"
    ppk_str = f"{ppk:.2f}" if not math.isnan(ppk) else "N/A"
    metrics_bullet = (
        f"Pp = {pp_str}, Ppk = {ppk_str}, "
        f"Mean = {cap['mean']:.3f}, σ = {cap['sigma_overall']:.3f}, "
        f"PPM = {cap['total_ppm']:.0f}, N = {n_batches} batches"
    )

    # --- Trend note ---
    trend_note = _assess_trend(limits["xbar"])

    # --- OOC summary ---
    if not violations:
        ooc_summary = "No out-of-control events detected."
        action_items = ""
    else:
        n_violations = len(violations)
        # Determine date range of violations if batch_ids/dates provided
        if batch_ids and dates and violations:
            viol_indices = sorted(set(v["batch_index"] for v in violations))
            valid = [i for i in viol_indices if i < len(batch_ids)]
            if valid:
                first_date = dates[valid[0]]
                last_date = dates[valid[-1]]
                first_batch = batch_ids[valid[0]]
                last_batch = batch_ids[valid[-1]]
                ooc_summary = (
                    f"{n_violations} out-of-control event(s) detected: "
                    f"{first_batch} ({first_date}) through "
                    f"{last_batch} ({last_date})."
                )
            else:
                ooc_summary = f"{n_violations} out-of-control event(s) detected."
        else:
            ooc_summary = f"{n_violations} out-of-control event(s) detected."

        action_items = "Investigate root cause of out-of-control signals and implement corrective actions."
        if ppk < 1.0:
            action_items += " Consider reviewing process parameters and specification limits."

    return {
        "verdict": verdict,
        "metrics_bullet": metrics_bullet,
        "trend_note": trend_note,
        "ooc_summary": ooc_summary,
        "action_items": action_items,
    }


def _assess_trend(xbar: np.ndarray) -> str:
    """Assess the direction of the xbar series using a simple slope check.

    Uses linear regression slope on the last min(10, len) points.
    """
    n = len(xbar)
    if n < 5:
        return "Insufficient data for trend assessment."

    window = min(10, n)
    recent = xbar[-window:]
    x = np.arange(window, dtype=float)
    y = recent.astype(float)

    # Simple linear regression slope
    x_mean = np.mean(x)
    y_mean = np.mean(y)
    slope = np.sum((x - x_mean) * (y - y_mean)) / (np.sum((x - x_mean) ** 2) + 1e-12)

    # Normalize slope relative to mean
    relative_slope = slope / (y_mean + 1e-12)

    if relative_slope > 0.005:
        return "Upward trend detected in recent batches."
    elif relative_slope < -0.005:
        return "Downward trend detected in recent batches."
    else:
        return "No significant trend detected."
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_narrative.py -v`
Expected: All 5 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add reports/__init__.py reports/narrative.py tests/test_narrative.py
git commit -m "feat: add narrative generator for auto-generated SPC report summaries"
```

---

### Task 3: Create `reports/pptx_generator.py`

**Files:**
- Create: `reports/pptx_generator.py`
- Test: `tests/test_pptx_generator.py`

- [ ] **Step 1: Write the failing test**

Create `D:\coding_is_fun\SPC\tests\test_pptx_generator.py`:

```python
import io
import numpy as np
import math
from pptx import Presentation
from reports.pptx_generator import build_report, _fig_to_image


def test_fig_to_image_returns_bytes():
    """Verify kaleido renders a Plotly figure to PNG bytes."""
    import plotly.graph_objects as go
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[1, 2, 3], y=[1, 2, 3]))
    img_bytes = _fig_to_image(fig, width=800, height=400)
    assert isinstance(img_bytes, bytes)
    assert len(img_bytes) > 100  # non-trivial PNG
    # PNG magic bytes
    assert img_bytes[:4] == b'\x89PNG'


def test_build_report_returns_bytesio():
    """Verify build_report returns a BytesIO containing a valid PPTX."""
    import plotly.graph_objects as go

    # Build minimal chart figures
    fig_xbar = go.Figure()
    fig_xbar.add_trace(go.Scatter(x=[1, 2, 3], y=[8.5, 8.4, 8.6]))
    fig_xbar.update_layout(title="X-bar & R Test", height=400)

    fig_cap = go.Figure()
    fig_cap.add_trace(go.Histogram(x=[8.5, 8.4, 8.6]))
    fig_cap.update_layout(title="Capability Test", height=300)

    fig_ppk = go.Figure()
    fig_ppk.add_trace(go.Scatter(x=[1, 2, 3], y=[1.5, 1.4, 1.6]))
    fig_ppk.update_layout(title="Rolling Ppk Test", height=300)

    summary = {
        "verdict": "Process is capable (Ppk = 1.52).",
        "metrics_bullet": "Pp = 1.80, Ppk = 1.52, Mean = 8.450, σ = 0.930, PPM = 127, N = 40 batches",
        "trend_note": "No significant trend detected.",
        "ooc_summary": "No out-of-control events detected.",
        "action_items": "",
    }
    metadata = {
        "formula": "Coating A",
        "parameter": "adhesion",
        "date_range": ("2025-01-01", "2025-03-15"),
        "generated_at": "2025-03-20 14:30",
        "baseline_n": 20,
    }

    result = build_report(
        fig_xbar=fig_xbar,
        fig_capability=fig_cap,
        fig_rolling_ppk=fig_ppk,
        summary=summary,
        metadata=metadata,
    )

    assert isinstance(result, io.BytesIO)
    result.seek(0)

    # Verify it's a valid PPTX
    prs = Presentation(result)
    assert len(prs.slides) == 5

    # Slide 1: Title — should contain formula and parameter
    slide1_text = " ".join(
        shape.text for shape in prs.slides[0].shapes if shape.has_text_frame
    )
    assert "Coating A" in slide1_text
    assert "adhesion" in slide1_text

    # Slide 2: Summary — should contain the verdict
    slide2_text = " ".join(
        shape.text for shape in prs.slides[1].shapes if shape.has_text_frame
    )
    assert "capable" in slide2_text.lower()
    assert "1.52" in slide2_text

    # Slides 3-5: should contain images (the chart PNGs)
    for slide_idx in [2, 3, 4]:
        shapes = prs.slides[slide_idx].shapes
        has_picture = any(shape.shape_type == 13 for shape in shapes)  # MSO_SHAPE_TYPE.PICTURE
        assert has_picture, f"Slide {slide_idx + 1} should contain an embedded chart image"


def test_build_report_with_ooc_events():
    """Verify OOC events appear in summary slide text."""
    import plotly.graph_objects as go

    fig_xbar = go.Figure()
    fig_xbar.add_trace(go.Scatter(x=[1, 2], y=[8.5, 8.4]))
    fig_xbar.update_layout(height=400)

    fig_cap = go.Figure()
    fig_cap.update_layout(height=300)

    fig_ppk = go.Figure()
    fig_ppk.update_layout(height=300)

    summary = {
        "verdict": "Process is marginal (Ppk = 1.08).",
        "metrics_bullet": "Pp = 1.10, Ppk = 1.08, Mean = 8.450, PPM = 5500",
        "trend_note": "Downward trend detected in recent batches.",
        "ooc_summary": "3 out-of-control event(s) detected: B-012 (2025-03-12) through B-018 (2025-03-18).",
        "action_items": "Investigate root cause of out-of-control signals.",
    }
    metadata = {
        "formula": "Coating A", "parameter": "adhesion",
        "date_range": ("2025-03-01", "2025-03-28"),
        "generated_at": "2025-03-20", "baseline_n": 10,
    }

    result = build_report(
        fig_xbar=fig_xbar, fig_capability=fig_cap, fig_rolling_ppk=fig_ppk,
        summary=summary, metadata=metadata,
    )
    result.seek(0)
    prs = Presentation(result)

    slide2_text = " ".join(
        shape.text for shape in prs.slides[1].shapes if shape.has_text_frame
    )
    assert "marginal" in slide2_text.lower()
    assert "3 out-of-control" in slide2_text.lower()
    assert "investigate" in slide2_text.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_pptx_generator.py -v`
Expected: FAIL with `ImportError: cannot import name 'build_report'`

- [ ] **Step 3: Implement pptx_generator.py**

Create `D:\coding_is_fun\SPC\reports\pptx_generator.py`:

```python
"""PPTX report generator for SPC analysis.

Builds a 5-slide PowerPoint deck from Plotly chart figures, capability data,
and narrative text. Pure Python — no Streamlit imports.
"""

import io
from datetime import datetime
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor

# --- Color palette (Corporate Professional) ---
NAVY = RGBColor(0x1E, 0x3A, 0x5F)
STEEL_BLUE = RGBColor(0x4A, 0x90, 0xD9)
DARK_GRAY = RGBColor(0x33, 0x33, 0x33)
MEDIUM_GRAY = RGBColor(0x66, 0x66, 0x66)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_GRAY = RGBColor(0xF5, 0xF5, 0xF5)

# --- Typography ---
FONT_FAMILY = "Calibri"


def _fig_to_image(fig, width: int = 1200, height: int = 600) -> bytes:
    """Render a Plotly Figure to PNG bytes via kaleido."""
    return fig.to_image(format="png", width=width, height=height, scale=2)


def _add_title_shape(slide, left, top, width, height, text, font_size=36,
                     font_color=WHITE, bold=True, alignment=PP_ALIGN.LEFT):
    """Add a text box to a slide with consistent styling."""
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.color.rgb = font_color
    p.font.bold = bold
    p.font.name = FONT_FAMILY
    p.alignment = alignment
    return txBox


def _add_body_text(slide, left, top, width, height, text,
                  font_size=14, font_color=DARK_GRAY, alignment=PP_ALIGN.LEFT):
    """Add a body text box to a slide."""
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.color.rgb = font_color
    p.font.name = FONT_FAMILY
    p.alignment = alignment
    return txBox


def _add_body_paragraphs(slide, left, top, width, height, paragraphs_data):
    """Add a text box with multiple styled paragraphs.

    paragraphs_data: list of dicts with keys: text, font_size, font_color, bold, space_after
    """
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True

    for i, pd in enumerate(paragraphs_data):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()

        p.text = pd.get("text", "")
        p.font.size = Pt(pd.get("font_size", 14))
        p.font.color.rgb = pd.get("font_color", DARK_GRAY)
        p.font.bold = pd.get("bold", False)
        p.font.name = FONT_FAMILY
        p.alignment = pd.get("alignment", PP_ALIGN.LEFT)
        if "space_after" in pd:
            p.space_after = Pt(pd["space_after"])

    return txBox


def _fill_navy_background(slide):
    """Set slide background to navy."""
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = NAVY


def _fill_white_background(slide):
    """Set slide background to white."""
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = WHITE


def _add_kpi_table(slide, left, top, width, height, cap, n_batches):
    """Add a capability KPI table to the slide."""
    rows = len(cap) + 1  # header + data rows
    cols = 2
    table_shape = slide.shapes.add_table(rows, cols, left, top, width, height)
    table = table_shape.table

    # Column widths
    table.columns[0].width = int(width * 0.5)
    table.columns[1].width = int(width * 0.5)

    # Header row
    for j, header in enumerate(["Metric", "Value"]):
        cell = table.cell(0, j)
        cell.text = header
        for paragraph in cell.text_frame.paragraphs:
            paragraph.font.size = Pt(11)
            paragraph.font.bold = True
            paragraph.font.color.rgb = WHITE
            paragraph.font.name = FONT_FAMILY
        cell.fill.solid()
        cell.fill.fore_color.rgb = NAVY

    # Data rows
    metric_rows = [
        ("Pp", f"{cap['Pp']:.2f}" if not math.isnan(cap["Pp"]) else "N/A"),
        ("Ppk", f"{cap['Ppk']:.2f}" if not math.isnan(cap["Ppk"]) else "N/A"),
        ("Mean", f"{cap['mean']:.3f}"),
        ("σ overall", f"{cap['sigma_overall']:.3f}"),
        ("PPM Total", f"{cap['total_ppm']:.0f}"),
        ("Batches", str(n_batches)),
    ]

    for i, (label, value) in enumerate(metric_rows):
        for j, text in enumerate([label, value]):
            cell = table.cell(i + 1, j)
            cell.text = text
            for paragraph in cell.text_frame.paragraphs:
                paragraph.font.size = Pt(11)
                paragraph.font.name = FONT_FAMILY
                paragraph.font.color.rgb = DARK_GRAY
                if j == 1:
                    paragraph.alignment = PP_ALIGN.RIGHT
            cell.fill.solid()
            cell.fill.fore_color.rgb = LIGHT_GRAY if i % 2 == 0 else WHITE

    return table_shape


def build_report(
    fig_xbar,
    fig_capability,
    fig_rolling_ppk,
    summary: dict,
    metadata: dict,
    cap: dict | None = None,
    n_batches: int = 0,
) -> io.BytesIO:
    """Build a 5-slide SPC report PPTX.

    Parameters
    ----------
    fig_xbar : plotly.graph_objects.Figure
        X-bar & R control chart figure.
    fig_capability : plotly.graph_objects.Figure
        Capability histogram figure.
    fig_rolling_ppk : plotly.graph_objects.Figure
        Rolling Ppk trend figure.
    summary : dict
        Output from reports.narrative.build_summary().
    metadata : dict
        Keys: formula, parameter, date_range (tuple), generated_at (str),
              baseline_n (int).
    cap : dict or None
        Capability metrics dict (for KPI table). If None, table is omitted.
    n_batches : int
        Number of batches included in the analysis.

    Returns
    -------
    io.BytesIO
        PPTX file bytes, ready for download.
    """
    import math  # local import to avoid top-level if not needed

    prs = Presentation()
    prs.slide_width = Inches(13.333)  # 16:9 widescreen
    prs.slide_height = Inches(7.5)

    formula = metadata["formula"]
    parameter = metadata["parameter"]
    date_start, date_end = metadata["date_range"]
    generated_at = metadata.get("generated_at", datetime.now().strftime("%Y-%m-%d %H:%M"))
    baseline_n = metadata.get("baseline_n", 20)

    # ===== SLIDE 1: Title =====
    slide1 = prs.slides.add_slide(prs.slide_layouts[6])  # blank layout
    _fill_navy_background(slide1)

    _add_title_shape(
        slide1, Inches(1), Inches(2), Inches(11), Inches(1),
        "SPC Process Report", font_size=40, font_color=WHITE, alignment=PP_ALIGN.LEFT,
    )
    _add_title_shape(
        slide1, Inches(1), Inches(3.2), Inches(11), Inches(0.8),
        f"{formula} / {parameter}", font_size=28, font_color=STEEL_BLUE,
        bold=True, alignment=PP_ALIGN.LEFT,
    )
    _add_body_text(
        slide1, Inches(1), Inches(4.5), Inches(11), Inches(0.6),
        f"Date range: {date_start} → {date_end}", font_size=16,
        font_color=RGBColor(0xAA, 0xBB, 0xCC), alignment=PP_ALIGN.LEFT,
    )
    _add_body_text(
        slide1, Inches(1), Inches(5.2), Inches(11), Inches(0.6),
        f"Generated: {generated_at}", font_size=14,
        font_color=RGBColor(0x88, 0x99, 0xAA), alignment=PP_ALIGN.LEFT,
    )

    # ===== SLIDE 2: Executive Summary =====
    slide2 = prs.slides.add_slide(prs.slide_layouts[6])
    _fill_white_background(slide2)

    _add_title_shape(
        slide2, Inches(0.5), Inches(0.3), Inches(12), Inches(0.7),
        "Executive Summary", font_size=28, font_color=NAVY, alignment=PP_ALIGN.LEFT,
    )

    # Build paragraph data
    paras = [
        {"text": summary["verdict"], "font_size": 16, "bold": True,
         "font_color": DARK_GRAY, "space_after": 12},
        {"text": summary["metrics_bullet"], "font_size": 13, "font_color": MEDIUM_GRAY,
         "space_after": 12},
        {"text": summary["trend_note"], "font_size": 13, "font_color": MEDIUM_GRAY,
         "space_after": 8},
        {"text": summary["ooc_summary"], "font_size": 13, "font_color": DARK_GRAY,
         "space_after": 8},
    ]
    if summary["action_items"]:
        paras.append({
            "text": f"Action: {summary['action_items']}",
            "font_size": 13, "font_color": RGBColor(0xC4, 0x52, 0x3E),
            "bold": True, "space_after": 0,
        })

    _add_body_paragraphs(
        slide2, Inches(0.5), Inches(1.3), Inches(12), Inches(5.5), paras,
    )

    # ===== SLIDE 3: X-bar & R Chart =====
    slide3 = prs.slides.add_slide(prs.slide_layouts[6])
    _fill_white_background(slide3)

    _add_title_shape(
        slide3, Inches(0.5), Inches(0.2), Inches(12), Inches(0.6),
        "X-bar & R Control Chart", font_size=24, font_color=NAVY,
    )

    img_bytes_xbar = _fig_to_image(fig_xbar, width=1200, height=600)
    slide3.shapes.add_picture(
        io.BytesIO(img_bytes_xbar),
        Inches(0.5), Inches(0.9), Inches(12), Inches(5.5),
    )

    _add_body_text(
        slide3, Inches(0.5), Inches(6.6), Inches(12), Inches(0.4),
        f"Control limits frozen from the first {baseline_n} batch(es) (baseline window).",
        font_size=10, font_color=MEDIUM_GRAY,
    )

    # ===== SLIDE 4: Capability Analysis =====
    slide4 = prs.slides.add_slide(prs.slide_layouts[6])
    _fill_white_background(slide4)

    _add_title_shape(
        slide4, Inches(0.5), Inches(0.2), Inches(12), Inches(0.6),
        "Process Capability", font_size=24, font_color=NAVY,
    )

    # Left: histogram image
    img_bytes_cap = _fig_to_image(fig_capability, width=800, height=500)
    slide4.shapes.add_picture(
        io.BytesIO(img_bytes_cap),
        Inches(0.3), Inches(1.0), Inches(6.5), Inches(5.5),
    )

    # Right: KPI table (only if cap data provided)
    if cap is not None:
        _add_kpi_table(
            slide4, Inches(7.2), Inches(1.2), Inches(5.5), Inches(4.0),
            cap, n_batches,
        )

    # ===== SLIDE 5: Rolling Ppk Trend =====
    slide5 = prs.slides.add_slide(prs.slide_layouts[6])
    _fill_white_background(slide5)

    _add_title_shape(
        slide5, Inches(0.5), Inches(0.2), Inches(12), Inches(0.6),
        "Trend Analysis — Rolling Ppk", font_size=24, font_color=NAVY,
    )

    img_bytes_ppk = _fig_to_image(fig_rolling_ppk, width=1200, height=500)
    slide5.shapes.add_picture(
        io.BytesIO(img_bytes_ppk),
        Inches(0.5), Inches(0.9), Inches(12), Inches(5.5),
    )

    _add_body_text(
        slide5, Inches(0.5), Inches(6.6), Inches(12), Inches(0.4),
        "Rolling Ppk (window=10) — tracks capability stability over time.",
        font_size=10, font_color=MEDIUM_GRAY,
    )

    # ===== Write to BytesIO =====
    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf
```

Note: the `import math` at the top of `_add_kpi_table` is not needed there — remove it. The `math.isnan` calls are only inside `_add_kpi_table` which uses the `cap` dict values. Add `import math` at the **top of the file** instead.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_pptx_generator.py -v`
Expected: All 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add reports/pptx_generator.py tests/test_pptx_generator.py
git commit -m "feat: add PPTX report generator with 5-slide template"
```

---

### Task 4: Add "Export Report" tab to Engineer page

**Files:**
- Modify: `D:\coding_is_fun\SPC\ui\engineer\chart_view.py`

- [ ] **Step 1: Read the current chart_view.py**

Confirm the current state (already read above). The key integration points:
- Line 117: `tab1, tab2, tab3, tab4 = st.tabs(...)` — add a 5th tab here
- Lines 90–99: SPC computation block — the data needed for the report is already computed here
- Lines 117–160: Tab content blocks — add the new tab block

- [ ] **Step 2: Add the export tab imports and helper function**

At the top of `chart_view.py`, add these imports after the existing ones:

```python
import io
from datetime import datetime
from reports.pptx_generator import build_report
from reports.narrative import build_summary
```

Add a helper function `_render_export_tab` after the existing `_ppk_status` function (before `render_spc_analysis`):

```python
def _render_export_tab(repo, df, selected_formula, selected_param,
                       limits, violations, cap, lsl, usl, has_lsl, has_usl,
                       dates, batch_ids):
    """Render the Export Report tab: generate PPTX and offer download."""
    from visualization.capability import build_capability_chart
    from visualization.rolling_ppk import build_rolling_ppk_chart
    from visualization.control_charts import build_xbar_r_chart

    st.subheader("📥 Export PowerPoint Report")

    st.caption(
        "Generate a 5-slide PowerPoint deck with SPC charts, capability metrics, "
        "and an executive summary for the currently selected formula/parameter."
    )

    if st.button("🟦 Generate PowerPoint", type="primary", key="gen_pptx"):
        target = (lsl + usl) / 2 if (has_lsl and has_usl) else None

        # Build the three chart figures
        fig_xbar = build_xbar_r_chart(
            limits, violations,
            f"{selected_formula} — {selected_param}", batch_ids,
        )
        fig_cap = build_capability_chart(
            limits["xbar"], lsl, usl, target,
            f"{selected_formula} — {selected_param}",
        )
        fig_ppk = build_rolling_ppk_chart(
            df, f"{selected_formula} — {selected_param}",
            lsl if has_lsl else None, usl if has_usl else None,
        )

        # Build narrative
        summary = build_summary(
            cap=cap, violations=violations, limits=limits,
            formula=selected_formula, parameter=selected_param,
            date_range=(dates[0], dates[-1]),
            n_batches=len(df),
            batch_ids=batch_ids, dates=dates,
        )

        # Build metadata
        metadata = {
            "formula": selected_formula,
            "parameter": selected_param,
            "date_range": (dates[0], dates[-1]),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "baseline_n": limits["baseline_n"],
        }

        # Generate PPTX
        buf = build_report(
            fig_xbar=fig_xbar,
            fig_capability=fig_cap,
            fig_rolling_ppk=fig_ppk,
            summary=summary,
            metadata=metadata,
            cap=cap,
            n_batches=len(df),
        )

        st.session_state["pptx_bytes"] = buf.getvalue()
        st.session_state["pptx_filename"] = (
            f"SPC_Report_{selected_formula}_{selected_param}_"
            f"{dates[-1]}.pptx"
        )
        st.session_state["pptx_generated"] = True

    # Show download button if generated
    if st.session_state.get("pptx_generated"):
        emoji, label, _ = _ppk_status(cap["Ppk"])
        st.success(
            f"Report ready — {selected_formula} / {selected_param}, "
            f"{len(df)} batches, {emoji} {label} (Ppk = {cap['Ppk']:.2f})"
        )
        st.download_button(
            label="⬇️ Download Report",
            data=st.session_state["pptx_bytes"],
            file_name=st.session_state["pptx_filename"],
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            key="dl_pptx",
        )
```

- [ ] **Step 3: Add the 5th tab to the tabs declaration**

In `chart_view.py`, change line 117 from:

```python
    tab1, tab2, tab3, tab4 = st.tabs(["X-bar & R", "Run Chart", "Moving Range", "Rolling Ppk"])
```

to:

```python
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["X-bar & R", "Run Chart", "Moving Range", "Rolling Ppk", "📥 Export Report"])
```

- [ ] **Step 4: Add the tab5 content block**

After the `with tab4:` block (after line 160), add:

```python
    with tab5:
        _render_export_tab(
            repo, df, selected_formula, selected_param,
            limits, violations, cap, lsl, usl, has_lsl, has_usl,
            dates, batch_ids,
        )
```

- [ ] **Step 5: Run the app to verify manually**

Run: `streamlit run app.py`
Steps:
1. Select "Engineer" role
2. Select a formula and parameter
3. Click the new "📥 Export Report" tab
4. Click "Generate PowerPoint"
5. Verify download button appears and the PPTX opens correctly in PowerPoint

- [ ] **Step 6: Run all tests to make sure nothing broke**

Run: `python -m pytest tests/ -v`
Expected: All tests PASS (including new narrative and pptx_generator tests).

- [ ] **Step 7: Commit**

```bash
git add ui/engineer/chart_view.py
git commit -m "feat: add Export Report tab to Engineer page with PPTX generation"
```

---

### Task 5: Run full test suite and final verification

- [ ] **Step 1: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: All tests PASS (40 existing + 8 new = 48 total).

- [ ] **Step 2: Verify end-to-end via Streamlit**

Run: `streamlit run app.py`
Verify:
1. Engineer page loads with 5 tabs
2. "Export Report" tab shows generate button
3. Clicking "Generate" produces a downloadable PPTX
4. PPTX opens with 5 slides: navy title, summary, X-bar/R chart, capability, rolling Ppk
5. Summary text matches the selected formula/parameter data

- [ ] **Step 3: Final commit (if any cleanup needed)**

```bash
git add -A
git commit -m "chore: final cleanup for PPTX report export feature"
```
