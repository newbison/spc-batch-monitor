import streamlit as st
import pandas as pd
import math

from data_access.repository import CsvRepository
from spc_engine.control_limits import compute_xbar_r
from spc_engine.rules import check_rules
from spc_engine.capability import compute_capability
from visualization.control_charts import build_xbar_r_chart
from visualization.capability import build_capability_chart


def render_spc_analysis(repo: CsvRepository, default_param: str | None = None):
    st.header("📈 SPC Analysis")

    df_all = repo.load_all()
    if df_all.empty:
        st.warning("No data available. Upload or enter data first.")
        return

    # --- Formula selector at the top ---
    formulas = sorted(df_all["formula"].unique().tolist())
    selected_formula = st.selectbox("Formula", formulas, key="eng_formula")

    # Filter by formula
    df_formula = df_all[df_all["formula"] == selected_formula]

    # --- Parameter selector ---
    params = sorted(df_formula["parameter"].unique().tolist())
    default_idx = params.index(default_param) if default_param and default_param in params else 0
    selected_param = st.selectbox("Parameter", params, index=default_idx, key="eng_param")

    # Filter by parameter
    df = df_formula[df_formula["parameter"] == selected_param].sort_values("date").reset_index(drop=True)

    if df.empty:
        st.warning(f"No data for {selected_param} in {selected_formula}.")
        return

    # --- SPC Computation ---
    limits = compute_xbar_r(df)
    violations = check_rules(limits["xbar"], limits["UCLx"], limits["LCLx"], limits["CLx"])
    batch_ids = df["batch_id"].tolist()
    dates = df["date"].tolist()

    # --- Control Limits Summary ---
    st.subheader("Control Limits")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("LCLₓ", f"{limits['LCLx']:.3f}")
    c2.metric("X̿", f"{limits['Xbarbar']:.3f}")
    c3.metric("UCLₓ", f"{limits['UCLx']:.3f}")
    c4.metric("R̄", f"{limits['Rbar']:.3f}")
    c5.metric("UCLᵣ", f"{limits['UCLr']:.3f}")

    # --- X-bar & R Chart ---
    st.subheader(f"X-bar & R Chart — {selected_formula} / {selected_param}")
    fig = build_xbar_r_chart(limits, violations, f"{selected_formula} — {selected_param}", batch_ids)
    st.plotly_chart(fig, use_container_width=True)

    # --- Violations ---
    if violations:
        st.subheader("⚠️ Out-of-Control Signals")
        viol_df = pd.DataFrame(violations)
        viol_df["batch"] = viol_df["batch_index"].apply(
            lambda i: f"{batch_ids[i]} ({dates[i]})" if i < len(batch_ids) else f"idx {i}"
        )
        st.dataframe(viol_df[["batch", "rule", "description"]],
                     use_container_width=True, hide_index=True)
    else:
        st.success("No out-of-control signals detected.")

    st.divider()

    # --- Capability Analysis ---
    st.subheader("Process Capability")

    lsl = float(df.iloc[-1]["lower_spec"])
    usl = float(df.iloc[-1]["upper_spec"])
    has_lsl = not math.isnan(lsl)
    has_usl = not math.isnan(usl)
    target = (lsl + usl) / 2 if (has_lsl and has_usl) else None

    cap = compute_capability(limits["xbar"], lsl, usl)

    # Spec info
    spec_parts = []
    if has_lsl:
        spec_parts.append(f"LSL = {lsl:.4g}")
    if has_usl:
        spec_parts.append(f"USL = {usl:.4g}")
    st.caption(f"Specs: {', '.join(spec_parts) if spec_parts else 'None'}")

    # KPIs
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Pp", f"{cap['Pp']:.2f}" if not math.isnan(cap["Pp"]) else "N/A")
    c2.metric("Ppk", f"{cap['Ppk']:.2f}" if not math.isnan(cap["Ppk"]) else "N/A")
    c3.metric("σ_overall", f"{cap['sigma_overall']:.3f}")
    c4.metric("Mean", f"{cap['mean']:.3f}")
    c5.metric("PPM Total", f"{cap['total_ppm']:.0f}")

    # Status
    if math.isnan(cap["Ppk"]):
        st.info("No spec limits defined for this parameter.")
    elif cap["Ppk"] >= 1.33:
        st.success("🟢 Process is capable (Ppk ≥ 1.33)")
    elif cap["Ppk"] >= 1.0:
        st.warning("🟡 Process is marginally capable (1.0 ≤ Ppk < 1.33)")
    else:
        st.error("🔴 Process is not capable (Ppk < 1.0)")

    # Histogram
    fig_cap = build_capability_chart(limits["xbar"], lsl, usl, target,
                                     f"{selected_formula} — {selected_param}")
    st.plotly_chart(fig_cap, use_container_width=True)

    # --- Raw Data ---
    st.divider()
    st.subheader("Raw Data")
    rep_cols = sorted([c for c in df.columns if c.startswith("rep")],
                      key=lambda x: int(x[3:]))
    display_cols = ["date", "batch_id"] + rep_cols
    display_df = df[display_cols].copy()
    display_df["X̄"] = limits["xbar"].round(3)
    display_df["R"] = limits["r"].round(3)
    st.dataframe(display_df.sort_values("date", ascending=False),
                 use_container_width=True, hide_index=True)
