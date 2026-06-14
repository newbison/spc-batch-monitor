import streamlit as st
import pandas as pd
import math
from datetime import datetime

from data_access.base import DataRepository
from spc_engine.control_limits import compute_xbar_r
from spc_engine.rules import check_rules
from spc_engine.capability import compute_capability
from visualization.control_charts import build_xbar_r_chart
from visualization.capability import build_capability_chart
from visualization.boxplot import build_boxplot_chart
from visualization.run_chart import build_run_chart
from visualization.moving_range import build_moving_range_chart
from visualization.rolling_ppk import build_rolling_ppk_chart
from reports.pptx_generator import build_report
from reports.narrative import build_summary


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


def _render_export_tab(df, selected_formula, selected_param,
                       limits, violations, cap, lsl, usl, has_lsl, has_usl,
                       dates, batch_ids):
    """Render the Export Report tab: generate PPTX and offer download."""
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


def render_spc_analysis(repo: DataRepository, default_param: str | None = None):
    st.markdown(
        "<h1 style='padding-top: 0; margin-top: -24px;'>SPC Analysis</h1>",
        unsafe_allow_html=True,
    )

    df_all = repo.load_all()
    if df_all.empty:
        st.warning("No data available. Upload or enter data first.")
        return

    # --- Compute status for all formula×parameter combos (for top warning) ---
    params_list = sorted(df_all["parameter"].unique().tolist())
    all_statuses = []
    for formula in sorted(df_all["formula"].unique()):
        for param in params_list:
            subset = df_all[(df_all["formula"] == formula) & (df_all["parameter"] == param)]
            if subset.empty:
                continue
            subset = subset.sort_values("date").reset_index(drop=True)
            limits_tmp = compute_xbar_r(subset)
            lsl_tmp = float(subset.iloc[-1]["lower_spec"])
            usl_tmp = float(subset.iloc[-1]["upper_spec"])
            cap_tmp = compute_capability(limits_tmp["xbar"], lsl_tmp, usl_tmp)
            emoji, label, _ = _ppk_status(cap_tmp["Ppk"])
            all_statuses.append({
                "Formula": formula, "Parameter": param,
                "Status": f"{emoji} {label}",
                "Ppk": cap_tmp["Ppk"],
            })

    # --- Out-of-spec warning banner (top of page, all formulas) ---
    red_items = [s for s in all_statuses if "🔴" in s["Status"]]
    yellow_items = [s for s in all_statuses if "🟡" in s["Status"]]
    if red_items:
        msg = "🔴 **Out of spec:** " + ", ".join(
            f"{s['Formula']} — {s['Parameter']} (Ppk={s['Ppk']:.2f})" for s in red_items)
        st.error(msg)
    if yellow_items:
        msg = "🟡 **Marginal:** " + ", ".join(
            f"{s['Formula']} — {s['Parameter']} (Ppk={s['Ppk']:.2f})" for s in yellow_items)
        st.warning(msg)

    # --- Formula + Parameter selectors side by side ---
    c_formula, c_param = st.columns(2)
    formulas = sorted(df_all["formula"].unique().tolist())
    selected_formula = c_formula.selectbox("Formula", formulas, key="eng_formula")

    df_formula = df_all[df_all["formula"] == selected_formula]
    params = sorted(df_formula["parameter"].unique().tolist())
    default_idx = params.index(default_param) if default_param and default_param in params else 0
    selected_param = c_param.selectbox("Parameter", params, index=default_idx, key="eng_param")

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

    # Spec limits (needed by tabs and capability section)
    lsl = float(df.iloc[-1]["lower_spec"])
    usl = float(df.iloc[-1]["upper_spec"])
    has_lsl = not math.isnan(lsl)
    has_usl = not math.isnan(usl)

    # --- Selected formula+param status banner ---
    cap = compute_capability(limits["xbar"], lsl, usl)
    if has_lsl or has_usl:
        if math.isnan(cap["Ppk"]):
            pass
        elif cap["Ppk"] >= 1.33:
            st.success(f"🟢 Process is capable — {selected_formula} / {selected_param} (Ppk = {cap['Ppk']:.2f})")
        elif cap["Ppk"] >= 1.0:
            st.warning(f"🟡 Process is marginal — {selected_formula} / {selected_param} (Ppk = {cap['Ppk']:.2f})")
        else:
            st.error(f"🔴 Process is NOT capable — {selected_formula} / {selected_param} (Ppk = {cap['Ppk']:.2f})")

    if violations:
        st.warning(f"⚠️ {len(violations)} out-of-control signal(s) detected — check X-bar & R tab for details")

    # --- Chart Tabs ---
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["X-bar & R", "Run Chart", "Moving Range", "Rolling Ppk", "📥 Export Report"])

    with tab1:
        st.subheader("Control Limits")
        st.caption(
            f"Limits frozen from the first **{limits['baseline_n']}** batch(es) "
            f"(baseline window). Newer points are judged against these limits."
        )
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("LCLₓ", f"{limits['LCLx']:.3f}")
        c2.metric("X̅̅", f"{limits['Xbarbar']:.3f}")
        c3.metric("UCLₓ", f"{limits['UCLx']:.3f}")
        c4.metric("R̄", f"{limits['Rbar']:.3f}")
        c5.metric("UCLᵣ", f"{limits['UCLr']:.3f}")

        st.subheader(f"X-bar & R Chart — {selected_formula} / {selected_param}")
        fig_xr = build_xbar_r_chart(limits, violations,
                                     f"{selected_formula} — {selected_param}", batch_ids)
        st.plotly_chart(fig_xr, use_container_width=True)

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

    with tab2:
        fig_run = build_run_chart(df, f"{selected_formula} — {selected_param}")
        st.plotly_chart(fig_run, use_container_width=True)

    with tab3:
        fig_mr = build_moving_range_chart(df, f"{selected_formula} — {selected_param}")
        st.plotly_chart(fig_mr, use_container_width=True)

    with tab4:
        fig_rppk = build_rolling_ppk_chart(df, f"{selected_formula} — {selected_param}",
                                            lsl if has_lsl else None,
                                            usl if has_usl else None)
        st.plotly_chart(fig_rppk, use_container_width=True)

    with tab5:
        _render_export_tab(
            df, selected_formula, selected_param,
            limits, violations, cap, lsl, usl, has_lsl, has_usl,
            dates, batch_ids,
        )

    st.divider()

    # --- Capability Analysis ---
    st.subheader("Process Capability")

    target = (lsl + usl) / 2 if (has_lsl and has_usl) else None

    # KPIs
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Pp", f"{cap['Pp']:.2f}" if not math.isnan(cap["Pp"]) else "N/A")
    c2.metric("Ppk", f"{cap['Ppk']:.2f}" if not math.isnan(cap["Ppk"]) else "N/A")
    c3.metric("σ_overall", f"{cap['sigma_overall']:.3f}")
    c4.metric("Mean", f"{cap['mean']:.3f}")
    c5.metric("PPM Total", f"{cap['total_ppm']:.0f}")

    # Histogram
    fig_cap = build_capability_chart(limits["xbar"], lsl, usl, target,
                                     f"{selected_formula} — {selected_param}")
    st.plotly_chart(fig_cap, use_container_width=True)

    # --- Boxplot by Batch ---
    with st.expander("Show Boxplot by Batch", expanded=True):
        fig_box = build_boxplot_chart(df, f"{selected_formula} — {selected_param}",
                                      lsl if has_lsl else None,
                                      usl if has_usl else None)
        st.plotly_chart(fig_box, use_container_width=True)

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
