import streamlit as st
import pandas as pd
import math
from datetime import date

from data_access.base import DataRepository
from spc_engine.control_limits import compute_xbar_r
from spc_engine.capability import compute_capability
from visualization.boxplot import build_boxplot_chart
from visualization.run_chart import build_run_chart
from visualization.moving_range import build_moving_range_chart
from visualization.rolling_ppk import build_rolling_ppk_chart


def _ppk_status(ppk: float) -> tuple[str, str, str]:
    """Return (emoji, label, color) for a Ppk value."""
    if math.isnan(ppk):
        return ("⚪", "No spec", "#888888")
    elif ppk >= 1.33:
        return ("🟢", "Capable", "#4CAF50")
    elif ppk >= 1.0:
        return ("🟡", "Marginal", "#FF9800")
    else:
        return ("🔴", "Not capable", "#f44336")


def render_dashboard(repo: DataRepository):
    st.header("📋 Management Dashboard")

    df = repo.load_all()
    if df.empty:
        st.warning("No data available.")
        return

    today_str = date.today().isoformat()

    # --- Warning Banner (computed before KPIs so it's at the very top) ---
    params_list = sorted(df["parameter"].unique().tolist())
    statuses = []
    for formula in sorted(df["formula"].unique()):
        for param in params_list:
            subset = df[(df["formula"] == formula) & (df["parameter"] == param)]
            if subset.empty:
                continue
            subset = subset.sort_values("date").reset_index(drop=True)
            limits = compute_xbar_r(subset)
            lsl = float(subset.iloc[-1]["lower_spec"])
            usl = float(subset.iloc[-1]["upper_spec"])
            cap = compute_capability(limits["xbar"], lsl, usl)
            emoji, label, color = _ppk_status(cap["Ppk"])
            statuses.append({
                "Formula": formula, "Parameter": param,
                "Status": f"{emoji} {label}",
                "Ppk": f"{cap['Ppk']:.2f}" if not math.isnan(cap["Ppk"]) else "N/A",
                "Pp": f"{cap['Pp']:.2f}" if not math.isnan(cap["Pp"]) else "N/A",
                "Mean": f"{cap['mean']:.3f}",
                "PPM": f"{cap['total_ppm']:.0f}",
                "N": len(subset),
            })

    red_items = [s for s in statuses if "🔴" in s["Status"]]
    yellow_items = [s for s in statuses if "🟡" in s["Status"]]
    if red_items:
        msg = "🔴 **Out of spec:** " + ", ".join(f"{s['Formula']} — {s['Parameter']}" for s in red_items)
        st.error(msg)
    if yellow_items:
        msg = "🟡 **Marginal:** " + ", ".join(f"{s['Formula']} — {s['Parameter']}" for s in yellow_items)
        st.warning(msg)

    # --- Top KPI Row ---
    st.subheader("Overview")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Formulas", df["formula"].nunique())
    k2.metric("Total Batches", df["batch_id"].nunique())
    k3.metric("Total Rows", len(df))
    today_count = (df["date"] == today_str).sum()
    k4.metric("Today's Uploads", today_count)

    st.divider()

    # --- Status Summary Cards ---
    st.subheader("Status Summary")

    status_df = pd.DataFrame(statuses)

    # Color-coded count cards
    green_count = sum(1 for s in statuses if "🟢" in s["Status"])
    yellow_count = sum(1 for s in statuses if "🟡" in s["Status"])
    red_count = sum(1 for s in statuses if "🔴" in s["Status"])
    grey_count = sum(1 for s in statuses if "⚪" in s["Status"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🟢 Capable", green_count)
    c2.metric("🟡 Marginal", yellow_count)
    c3.metric("🔴 Not Capable", red_count)
    c4.metric("⚪ No Spec", grey_count)

    # --- Full Status Table ---
    st.divider()
    st.subheader("All Formulas × Parameters")
    st.dataframe(status_df, use_container_width=True, hide_index=True,
                 column_config={
                     "Status": st.column_config.TextColumn("Status"),
                     "Ppk": st.column_config.TextColumn("Ppk"),
                     "Pp": st.column_config.TextColumn("Pp"),
                     "Mean": st.column_config.TextColumn("Mean"),
                     "PPM": st.column_config.TextColumn("PPM"),
                     "N": st.column_config.NumberColumn("Batches"),
                 })

    # --- Recent Activity ---
    st.divider()
    st.subheader("Recent Batches")
    recent = df.sort_values("date", ascending=False).head(15)
    rep_cols = sorted([c for c in df.columns if c.startswith("rep")],
                      key=lambda x: int(x[3:]))
    display_recent = recent[["date", "batch_id", "formula", "parameter"] + rep_cols]
    st.dataframe(display_recent, use_container_width=True, hide_index=True)

    # --- Boxplot by Batch ---
    with st.expander("Show Boxplot by Batch", expanded=True):
        c1, c2 = st.columns(2)
        box_formula = c1.selectbox("Formula", sorted(df["formula"].unique()), key="mgr_box_formula")
        box_param = c2.selectbox("Parameter", sorted(df["parameter"].unique()), key="mgr_box_param")
        subset = df[(df["formula"] == box_formula) & (df["parameter"] == box_param)] \
            .sort_values("date").reset_index(drop=True)
        if not subset.empty:
            lsl = float(subset.iloc[-1]["lower_spec"])
            usl = float(subset.iloc[-1]["upper_spec"])
            has_lsl = not math.isnan(lsl)
            has_usl = not math.isnan(usl)
            fig_box = build_boxplot_chart(subset, f"{box_formula} — {box_param}",
                                          lsl if has_lsl else None,
                                          usl if has_usl else None)
            st.plotly_chart(fig_box, use_container_width=True)

    # --- Trend Analysis ---
    with st.expander("Show Trend Analysis", expanded=True):
        tc1, tc2 = st.columns(2)
        trend_formula = tc1.selectbox("Formula", sorted(df["formula"].unique()),
                                       key="mgr_trend_formula")
        trend_param = tc2.selectbox("Parameter", sorted(df["parameter"].unique()),
                                     key="mgr_trend_param")
        chart_type = st.radio("Chart type:",
                              ["Run Chart", "Moving Range", "Rolling Ppk"],
                              horizontal=True, key="mgr_trend_type")

        subset = df[(df["formula"] == trend_formula) & (df["parameter"] == trend_param)] \
            .sort_values("date").reset_index(drop=True)
        if not subset.empty:
            lsl = float(subset.iloc[-1]["lower_spec"])
            usl = float(subset.iloc[-1]["upper_spec"])
            has_lsl = not math.isnan(lsl)
            has_usl = not math.isnan(usl)

            if chart_type == "Run Chart":
                fig = build_run_chart(subset, f"{trend_formula} — {trend_param}")
            elif chart_type == "Moving Range":
                fig = build_moving_range_chart(subset, f"{trend_formula} — {trend_param}")
            else:
                fig = build_rolling_ppk_chart(subset, f"{trend_formula} — {trend_param}",
                                               lsl if has_lsl else None,
                                               usl if has_usl else None)
            st.plotly_chart(fig, use_container_width=True)
