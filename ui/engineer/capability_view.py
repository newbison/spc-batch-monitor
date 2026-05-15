import streamlit as st
import math

from data_access.repository import CsvRepository
from spc_engine.control_limits import compute_xbar_r
from spc_engine.capability import compute_capability
from visualization.capability import build_capability_chart


def _get_specs_from_data(df) -> tuple[float, float]:
    """Extract specs from CSV data. Uses the most recent row. NaN = no limit."""
    row = df.iloc[-1]
    return float(row["lower_spec"]), float(row["upper_spec"])


def render_capability_view(repo: CsvRepository, parameter: str):
    st.header(f"📊 Process Capability — {parameter}")

    df = repo.get_for_parameter(parameter)

    if df.empty:
        st.warning(f"No data available for {parameter}. Enter data first.")
        return

    df = df.sort_values("date").reset_index(drop=True)
    limits = compute_xbar_r(df)
    xbar = limits["xbar"]

    lsl, usl = _get_specs_from_data(df)
    has_lsl = not math.isnan(lsl)
    has_usl = not math.isnan(usl)
    target = (lsl + usl) / 2 if (has_lsl and has_usl) else None

    cap = compute_capability(xbar, lsl, usl)

    # Show which specs are in play
    spec_parts = []
    if has_lsl:
        spec_parts.append(f"LSL = {lsl:.4g}")
    if has_usl:
        spec_parts.append(f"USL = {usl:.4g}")
    st.caption(f"Spec limits from data: {', '.join(spec_parts) if spec_parts else 'None'}")

    # KPI row
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Pp", f"{cap['Pp']:.2f}" if not math.isnan(cap["Pp"]) else "N/A")
    col2.metric("Ppk", f"{cap['Ppk']:.2f}" if not math.isnan(cap["Ppk"]) else "N/A")
    col3.metric("σ_overall", f"{cap['sigma_overall']:.3f}")
    col4.metric("Mean", f"{cap['mean']:.3f}")
    col5.metric("PPM Total", f"{cap['total_ppm']:.0f}")

    # Interpretation
    if math.isnan(cap["Ppk"]):
        st.info("No spec limits defined for this parameter.")
    elif cap["Ppk"] >= 1.33:
        st.success("Process is capable (Ppk ≥ 1.33)")
    elif cap["Ppk"] >= 1.0:
        st.warning("Process is marginally capable (1.0 ≤ Ppk < 1.33)")
    else:
        st.error("Process is not capable (Ppk < 1.0)")

    # Histogram
    fig = build_capability_chart(xbar, lsl, usl, target, parameter)
    st.plotly_chart(fig, use_container_width=True)
