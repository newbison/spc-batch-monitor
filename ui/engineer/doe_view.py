"""DOE (Design of Experiments) page — Streamlit wizard UI.

Multi-entry wizard: Landing -> Define -> Design -> Capture -> Analyze -> Optimize.
"""

import json
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from data_access.base import DataRepository
from doe.persistence import DoeRepository
from config import DB_FILE

# JSON persistence key prefix for session state
DOE_REPO_KEY = "doe_repo"


def _get_doe_repo() -> DoeRepository:
    """Get or create the DOE repository (shares spc.db)."""
    if DOE_REPO_KEY not in st.session_state:
        st.session_state[DOE_REPO_KEY] = DoeRepository(DB_FILE)
    return st.session_state[DOE_REPO_KEY]


def render_doe_page(repo: DataRepository):
    """Main entry point for the DOE page."""
    doe_repo = _get_doe_repo()

    st.title("Design of Experiments")

    # Initialize wizard state
    if "doe_step" not in st.session_state:
        st.session_state.doe_step = "landing"
    if "doe_session" not in st.session_state:
        st.session_state.doe_session = None

    step = st.session_state.doe_step

    if step == "landing":
        _render_landing(doe_repo)
    elif step == "define":
        _render_define(doe_repo)
    elif step == "design":
        _render_design(doe_repo)
    elif step == "capture":
        _render_capture(doe_repo)
    elif step == "analyze":
        _render_analyze(doe_repo)
    elif step == "optimize":
        _render_optimize(doe_repo)


def _go_to(step: str):
    """Navigate to a wizard step."""
    st.session_state.doe_step = step


def _reset_doe():
    """Reset the wizard to landing."""
    st.session_state.doe_step = "landing"
    st.session_state.doe_session = None
    st.rerun()


# ---------------------------------------------------------------------------
# Landing page
# ---------------------------------------------------------------------------

def _render_landing(doe_repo: DoeRepository):
    """Landing page: choose entry type or resume existing."""
    st.subheader("Start a DOE")

    # Resume existing
    saved = doe_repo.list_sessions()
    if saved:
        st.markdown("#### Continue existing DOE")
        cols = st.columns([3, 1])
        with cols[0]:
            selected_name = st.selectbox(
                "Saved sessions",
                options=[f"{s['id']}: {s['name']} ({s['entry_type']}, {s['status']})"
                         for s in saved],
                key="doe_resume_select",
            )
        with cols[1]:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Resume", key="doe_resume_btn"):
                sid = int(selected_name.split(":")[0])
                session = doe_repo.load(sid)
                # Reconstruct session state from DB
                st.session_state.doe_session = {
                    "name": session["name"],
                    "entry_type": session["entry_type"],
                    "status": session["status"],
                    "factors_json": json.loads(session["factors"]) if session["factors"] else [],
                    "responses_json": json.loads(session["responses"]) if session["responses"] else [],
                    "design_json": json.loads(session["design"]) if session.get("design") else None,
                    "results_json": json.loads(session["results"]) if session.get("results") else None,
                    "model_json": json.loads(session["model"]) if session.get("model") else None,
                    "optimum_json": json.loads(session["optimum"]) if session.get("optimum") else None,
                    "db_id": sid,
                }
                # Navigate to the appropriate step
                status_to_step = {
                    "defined": "define",
                    "designed": "design",
                    "running": "capture",
                    "analyzed": "analyze",
                    "optimized": "optimize",
                }
                _go_to(status_to_step.get(session["status"], "define"))
                st.rerun()

        st.divider()

    st.markdown("#### Start new DOE")
    entry_type = st.radio(
        "Entry type",
        options=["screening", "full_factorial", "analyze_only"],
        format_func=lambda x: {
            "screening": "Screening — find critical factors from many",
            "full_factorial": "Full factorial — characterize known critical factors",
            "analyze_only": "Analyze only — import existing results",
        }[x],
        key="doe_entry_type",
    )

    if st.button("Start  ->", type="primary", key="doe_start_btn"):
        st.session_state.doe_session = {
            "name": "",
            "entry_type": entry_type,
            "status": "defined",
            "factors_json": [],
            "responses_json": [],
            "design_json": None,
            "results_json": None,
            "model_json": None,
            "optimum_json": None,
        }
        _go_to("define")
        st.rerun()


# ---------------------------------------------------------------------------
# Step 1: Define factors and responses
# ---------------------------------------------------------------------------

def _render_define(doe_repo: DoeRepository):
    """Step 1: Define factors and responses."""
    session = st.session_state.doe_session
    entry_type = session["entry_type"]

    st.subheader("Step 1: Define Factors & Responses")
    st.caption(f"Entry type: {entry_type.replace('_', ' ').title()}")

    # DOE name
    session["name"] = st.text_input("DOE Name", value=session.get("name", ""),
                                     key="doe_name_input")

    # --- Factors ---
    st.markdown("##### Factors")
    factors = session.get("factors_json", [])

    if not factors:
        factors = [{"name": "", "type": "continuous", "low": 0, "high": 100}]

    edited_factors = st.data_editor(
        pd.DataFrame(factors),
        num_rows="dynamic",
        use_container_width=True,
        key="doe_factors_editor",
        column_config={
            "name": st.column_config.TextColumn("Factor Name", required=True),
            "type": st.column_config.SelectboxColumn(
                "Type", options=["continuous", "categorical"], required=True
            ),
            "low": st.column_config.NumberColumn("Low", required=True),
            "high": st.column_config.NumberColumn("High", required=True),
        },
        hide_index=True,
    )
    session["factors_json"] = edited_factors.to_dict("records")

    # --- Responses ---
    st.markdown("##### Responses")
    responses = session.get("responses_json", [])

    if not responses:
        responses = [{"name": "", "goal": "maximize", "target": None, "low": 0, "high": 100}]

    edited_responses = st.data_editor(
        pd.DataFrame(responses),
        num_rows="dynamic",
        use_container_width=True,
        key="doe_responses_editor",
        column_config={
            "name": st.column_config.TextColumn("Response Name", required=True),
            "goal": st.column_config.SelectboxColumn(
                "Goal", options=["maximize", "minimize", "target"], required=True
            ),
            "target": st.column_config.NumberColumn("Target (for 'target' goal only)"),
            "low": st.column_config.NumberColumn("Low Bound", required=True),
            "high": st.column_config.NumberColumn("High Bound", required=True),
        },
        hide_index=True,
    )
    session["responses_json"] = edited_responses.to_dict("records")

    st.divider()

    # Navigation
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("<- Back", key="doe_define_back"):
            _reset_doe()
    with col2:
        if st.button("Next: Design  ->", type="primary", key="doe_define_next"):
            # Validate
            valid_factors = [f for f in session["factors_json"]
                             if f.get("name") and str(f.get("name")).strip()]
            valid_responses = [r for r in session["responses_json"]
                               if r.get("name") and str(r.get("name")).strip()]

            if not valid_factors:
                st.error("Add at least one factor with a name.")
                return
            if not valid_responses:
                st.error("Add at least one response with a name.")
                return

            session["factors_json"] = valid_factors
            session["responses_json"] = valid_responses

            # Save to DB
            sid = doe_repo.create(
                name=session["name"] or "Untitled DOE",
                entry_type=session["entry_type"],
                factors=valid_factors,
                responses=valid_responses,
            )
            st.session_state.doe_session_id = sid
            st.session_state.doe_session["db_id"] = sid

            if session["entry_type"] == "analyze_only":
                _go_to("capture")
            else:
                _go_to("design")
            st.rerun()


# ---------------------------------------------------------------------------
# Step 2: Generate Design
# ---------------------------------------------------------------------------

def _render_design(doe_repo: DoeRepository):
    """Step 2: Generate and display the design matrix."""
    session = st.session_state.doe_session
    entry_type = session["entry_type"]
    factors = session.get("factors_json", [])
    responses = session.get("responses_json", [])
    db_id = session.get("db_id")

    st.subheader("Step 2: Generate Design")

    # Design parameters
    col1, col2 = st.columns(2)
    with col1:
        n_factors = len(factors)
        if entry_type == "screening":
            resolution = st.selectbox(
                "Resolution",
                options=[4, 5],
                index=0,
                help="Resolution IV: main effects clear of 2-factor interactions. "
                     "Resolution V: main effects + 2-way interactions clear of each other.",
                key="doe_resolution",
            )
            n_runs = 2 ** (n_factors - 1) if resolution >= 4 else 2 ** n_factors
            st.info(f"Estimated runs: {n_runs} (fractional factorial)")
        else:
            n_center = st.slider("Center points", min_value=0, max_value=5,
                                value=3, key="doe_n_center")
            n_runs = 2 ** n_factors + n_center
            st.info(f"Total runs: {2 ** n_factors} factorial + {n_center} center = {n_runs}")

    st.divider()

    if st.button("Generate Run Sheet", type="primary", key="doe_gen_design"):
        from doe.designs import (
            generate_full_factorial,
            generate_fractional_factorial,
            add_center_points,
            decode_to_actual,
        )

        if entry_type == "screening":
            coded_df = generate_fractional_factorial(factors, resolution=4)
        else:
            coded_df = generate_full_factorial(factors, n_center=n_center)

        # Decode for display
        decoded_df = decode_to_actual(coded_df, factors)

        session["design_json"] = coded_df.to_dict("records")
        session["design_df"] = decoded_df  # keep DataFrame for display

        # Save design to DB
        if db_id:
            doe_repo.update(db_id, {
                "design": coded_df.to_dict("records"),
                "status": "designed",
            })

        st.rerun()

    # Show design if generated
    if session.get("design_json"):
        decoded_df = session.get("design_df")
        if decoded_df is not None:
            st.markdown("##### Run Sheet (coded -> actual)")
            st.dataframe(decoded_df, use_container_width=True, hide_index=True)

            # Add blank response columns for download
            response_names = [r["name"] for r in responses]
            if response_names:
                download_df = decoded_df.copy()
                for rname in response_names:
                    download_df[rname] = ""
                st.download_button(
                    "Export Run Sheet (CSV)",
                    data=download_df.to_csv(index=False),
                    file_name=f"doe_run_sheet_{session.get('name', 'doe')}.csv",
                    mime="text/csv",
                    key="doe_download_runsheet",
                )

    st.divider()

    # Navigation
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("<- Back to Define", key="doe_design_back"):
            _go_to("define")
            st.rerun()
    with col2:
        if session.get("design_json"):
            if st.button("Next: Capture  ->", type="primary", key="doe_design_next"):
                _go_to("capture")
                st.rerun()


# ---------------------------------------------------------------------------
# Step 3: Capture Results
# ---------------------------------------------------------------------------

def _render_capture(doe_repo: DoeRepository):
    """Step 3: Capture response values (manual entry or CSV upload)."""
    session = st.session_state.doe_session
    design_json = session.get("design_json")
    factors = session.get("factors_json", [])
    responses = session.get("responses_json", [])
    db_id = session.get("db_id")

    st.subheader("Step 3: Capture Results")

    response_names = [r["name"] for r in responses]
    n_runs = len(design_json) if design_json else 0

    if not response_names:
        st.error("No responses defined. Go back to Define step.")
        if st.button("<- Back to Define", key="doe_capture_back_no_resp"):
            _go_to("define")
            st.rerun()
        return

    # Upload CSV option
    st.markdown("##### Upload completed run sheet")
    uploaded = st.file_uploader(
        "Upload CSV with response columns filled in",
        type=["csv"],
        key="doe_upload_csv",
    )

    if uploaded is not None:
        try:
            uploaded_df = pd.read_csv(uploaded)
            st.success(f"Loaded {len(uploaded_df)} rows from CSV")

            # Verify response columns exist
            missing = [r for r in response_names if r not in uploaded_df.columns]
            if missing:
                st.warning(f"Missing response columns: {missing}")

            # Extract results
            results = []
            for _, row in uploaded_df.iterrows():
                run_result = {"run": int(row["run"])}
                for rname in response_names:
                    if rname in uploaded_df.columns:
                        run_result[rname] = float(row[rname])
                results.append(run_result)

            session["results_json"] = results
            st.dataframe(uploaded_df, use_container_width=True)
        except Exception as e:
            st.error(f"Error reading CSV: {e}")
            return

    st.divider()

    # Manual entry option
    st.markdown("##### Or enter results manually")

    if not session.get("results_json"):
        # Initialize empty results table
        if design_json:
            empty_results = []
            for d in design_json:
                row = {"run": d["run"]}
                for rname in response_names:
                    row[rname] = None
                empty_results.append(row)
            session["results_json"] = empty_results

    if session.get("results_json"):
        results_df = pd.DataFrame(session["results_json"])
        edited = st.data_editor(
            results_df,
            num_rows="dynamic",
            use_container_width=True,
            key="doe_results_editor",
            column_config={
                "run": st.column_config.NumberColumn("Run", disabled=True),
                **{rname: st.column_config.NumberColumn(rname, required=True)
                   for rname in response_names},
            },
            hide_index=True,
        )
        session["results_json"] = edited.to_dict("records")

    st.divider()

    # Validate and proceed
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("<- Back to Design", key="doe_capture_back"):
            if session["entry_type"] == "analyze_only":
                _go_to("define")
            else:
                _go_to("design")
            st.rerun()
    with col2:
        if st.button("Next: Analyze  ->", type="primary", key="doe_capture_next"):
            # Validate all responses filled in
            results = session.get("results_json", [])
            valid = True
            for r in results:
                for rname in response_names:
                    val = r.get(rname)
                    if val is None or (isinstance(val, float) and pd.isna(val)):
                        st.error(f"Run {r['run']}: {rname} is missing.")
                        valid = False
            if not valid:
                return

            # Save to DB
            if db_id:
                doe_repo.update(db_id, {
                    "results": results,
                    "status": "running",
                })
            _go_to("analyze")
            st.rerun()


# ---------------------------------------------------------------------------
# Step 4: Analyze
# ---------------------------------------------------------------------------

def _render_analyze(doe_repo: DoeRepository):
    """Step 4: Analyze results with regression and visualization."""
    session = st.session_state.doe_session
    design_json = session.get("design_json")
    results_json = session.get("results_json")
    factors = session.get("factors_json", [])
    responses = session.get("responses_json", [])
    db_id = session.get("db_id")

    st.subheader("Step 4: Analysis")

    design_df = pd.DataFrame(design_json) if design_json else None
    results_df = pd.DataFrame(results_json) if results_json else None
    response_names = [r["name"] for r in responses]

    if design_df is None or results_df is None:
        st.error("Design or results missing. Go back and complete those steps.")
        return

    # Merge design + results
    merged = design_df.merge(results_df, on="run")
    factor_names = [f["name"] for f in factors]

    all_models = {}

    for rname in response_names:
        st.markdown(f"### Response: {rname}")

        # Fit linear model
        from doe.analysis import fit_linear, fit_rsm, has_curvature

        linear_model = fit_linear(factors, design_df, results_df, rname)

        # Coefficient table
        st.markdown("##### Coefficients (Linear Model)")
        coef_df = pd.DataFrame(linear_model["coefficients"])
        coef_df["p_value"] = coef_df["p_value"].map(lambda x: f"{x:.4f}")
        coef_df["estimate"] = coef_df["estimate"].map(lambda x: f"{x:.3f}")
        coef_df.rename(columns={
            "term": "Term", "estimate": "Estimate",
            "std_err": "Std Err", "p_value": "P-value",
            "significant": "Significant",
        }, inplace=True)
        st.dataframe(coef_df, use_container_width=True, hide_index=True)

        # Model summary metrics
        c1, c2, c3 = st.columns(3)
        c1.metric("R-squared", f"{linear_model['r_squared']:.4f}")
        c2.metric("Adj R-squared", f"{linear_model['r_squared_adj']:.4f}")
        c3.metric("Model p-value", f"{linear_model['model_p_value']:.4f}")

        # Check for center points -> RSM
        is_center = np.ones(len(merged), dtype=bool)
        for f in factor_names:
            is_center &= np.abs(merged[f].values) < 0.01

        has_center = is_center.sum() >= 3

        rsm_model = None
        if has_center:
            factorial_y = merged.loc[~is_center, rname].values
            center_y = merged.loc[is_center, rname].values

            if has_curvature(factorial_y, center_y):
                st.info("Curvature detected! Fitting RSM (quadratic) model.")
                rsm_model = fit_rsm(factors, design_df, results_df, rname)

                st.markdown("##### RSM Coefficients")
                rsm_coef_df = pd.DataFrame(rsm_model["coefficients"])
                rsm_coef_df["p_value"] = rsm_coef_df["p_value"].map(lambda x: f"{x:.4f}")
                rsm_coef_df["estimate"] = rsm_coef_df["estimate"].map(lambda x: f"{x:.3f}")
                rsm_coef_df.rename(columns={
                    "term": "Term", "estimate": "Estimate",
                    "std_err": "Std Err", "p_value": "P-value",
                    "significant": "Significant",
                }, inplace=True)
                st.dataframe(rsm_coef_df, use_container_width=True, hide_index=True)

        # --- Visualizations ---
        active_model = rsm_model if rsm_model else linear_model
        all_models[rname] = active_model

        # Main effects plot
        if len(factor_names) > 0:
            fig_main = _build_main_effects_plot(merged, factor_names, rname, active_model)
            st.plotly_chart(fig_main, use_container_width=True)

        # Pareto of effects
        fig_pareto = _build_pareto_plot(active_model)
        st.plotly_chart(fig_pareto, use_container_width=True)

        # Contour/surface plots (RSM only, 2+ significant continuous factors)
        if rsm_model and len(factor_names) >= 2:
            sig_continuous = [
                f for f in factors
                if f["type"] == "continuous"
                and any(c["term"] == f["name"] and c["significant"]
                        for c in rsm_model["coefficients"])
            ]
            if len(sig_continuous) >= 2:
                fig_contour = _build_contour_plot(
                    factors, rsm_model, rname, sig_continuous[0]["name"],
                    sig_continuous[1]["name"],
                )
                st.plotly_chart(fig_contour, use_container_width=True)

                fig_surface = _build_surface_plot(
                    factors, rsm_model, rname, sig_continuous[0]["name"],
                    sig_continuous[1]["name"],
                )
                st.plotly_chart(fig_surface, use_container_width=True)

        st.divider()

    # Save model to DB
    if db_id and st.button("Save Analysis", key="doe_save_analysis"):
        doe_repo.update(db_id, {
            "model": all_models,
            "status": "analyzed",
        })
        st.success("Analysis saved.")

    # Navigation
    st.divider()
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("<- Back to Capture", key="doe_analyze_back"):
            _go_to("capture")
            st.rerun()
    with col2:
        if st.button("Next: Optimize  ->", type="primary", key="doe_analyze_next"):
            session["model_json"] = all_models
            if db_id:
                doe_repo.update(db_id, {
                    "model": all_models,
                    "status": "analyzed",
                })
            _go_to("optimize")
            st.rerun()
    with col3:
        # Screening path: promote to full factorial
        if session["entry_type"] == "screening":
            if st.button("Promote to Full Factorial", key="doe_promote"):
                _promote_to_full_factorial(session, doe_repo, factors, responses, all_models)


# ---------------------------------------------------------------------------
# Step 5: Optimize
# ---------------------------------------------------------------------------

def _render_optimize(doe_repo: DoeRepository):
    """Step 5: Multi-response optimization via desirability."""
    session = st.session_state.doe_session
    factors = session.get("factors_json", [])
    responses = session.get("responses_json", [])
    models = session.get("model_json")
    db_id = session.get("db_id")

    st.subheader("Step 5: Optimization")

    if not models:
        st.error("No models fitted. Go back to Analyze step.")
        if st.button("<- Back to Analyze", key="doe_opt_back_no_model"):
            _go_to("analyze")
            st.rerun()
        return

    # Show editable response goals
    st.markdown("##### Response Goals")
    goal_edits = []
    for r in responses:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f"**{r['name']}**")
        with c2:
            goal = st.selectbox(
                "Goal", options=["maximize", "minimize", "target"],
                index=["maximize", "minimize", "target"].index(r["goal"]),
                key=f"doe_goal_{r['name']}",
            )
            r["goal"] = goal
        with c3:
            low = st.number_input("Low", value=r["low"], key=f"doe_low_{r['name']}")
            r["low"] = low
        with c4:
            high = st.number_input("High", value=r["high"], key=f"doe_high_{r['name']}")
            r["high"] = high
        if r["goal"] == "target":
            r["target"] = st.number_input(
                "Target", value=r.get("target") or r["low"],
                key=f"doe_target_{r['name']}",
            )
        goal_edits.append(r)

    st.divider()

    if st.button("Find Optimum", type="primary", key="doe_find_optimum"):
        from doe.optimization import optimize as doe_optimize

        result = doe_optimize(factors, responses, models, n_starts=10)
        session["optimum_json"] = result

        # Save to DB
        if db_id:
            doe_repo.update(db_id, {
                "optimum": result,
                "status": "optimized",
            })
        st.rerun()

    # Display results
    if session.get("optimum_json"):
        result = session["optimum_json"]
        st.markdown("### Optimal Settings")

        # Optimal factor settings
        cols = st.columns(len(factors))
        for i, f in enumerate(factors):
            val = result["optimal_settings"].get(f["name"], "—")
            unit_info = f" ({f['low']}-{f['high']})" if f["type"] == "continuous" else ""
            with cols[i]:
                st.metric(f["name"], f"{val}{unit_info}")

        # Predicted responses
        st.markdown("#### Predicted Responses")
        resp_cols = st.columns(len(responses))
        for i, r in enumerate(responses):
            pred = result["predicted_responses"].get(r["name"], "—")
            pi = result["prediction_intervals"].get(r["name"], ["—", "—"])
            with resp_cols[i]:
                st.metric(r["name"], f"{pred}")
                st.caption(f"95% PI: [{pi[0]} - {pi[1]}]")

        # Overall desirability
        st.markdown("#### Overall Desirability")
        d = result["desirability"]
        if d >= 0.8:
            st.success(f"D = {d:.3f} — Excellent")
        elif d >= 0.5:
            st.warning(f"D = {d:.3f} — Acceptable")
        else:
            st.error(f"D = {d:.3f} — Poor — consider adjusting response goals")

        # Download summary
        summary_rows = []
        summary_rows.append(["Optimal Settings"])
        for f in factors:
            summary_rows.append([f["name"], result["optimal_settings"].get(f["name"], "")])
        summary_rows.append([])
        summary_rows.append(["Predicted Responses"])
        for r in responses:
            pred = result["predicted_responses"].get(r["name"], "")
            pi = result["prediction_intervals"].get(r["name"], ["", ""])
            summary_rows.append([r["name"], pred, f"[{pi[0]}, {pi[1]}]"])
        summary_rows.append([])
        summary_rows.append(["Overall Desirability", d])

        summary_df = pd.DataFrame(summary_rows)
        st.download_button(
            "Download Summary (CSV)",
            data=summary_df.to_csv(index=False, header=False),
            file_name=f"doe_optimization_{session.get('name', 'doe')}.csv",
            mime="text/csv",
            key="doe_download_opt_summary",
        )

    st.divider()

    # Navigation
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("<- Back to Analyze", key="doe_opt_back"):
            _go_to("analyze")
            st.rerun()
    with col2:
        if st.button("New DOE", key="doe_new"):
            _reset_doe()


# ---------------------------------------------------------------------------
# Visualization helpers
# ---------------------------------------------------------------------------

def _build_main_effects_plot(merged: pd.DataFrame, factor_names: list[str],
                               response_name: str, model: dict) -> go.Figure:
    """Build a main effects plot: one subplot per factor."""
    n_factors = len(factor_names)
    fig = make_subplots(
        rows=1, cols=n_factors,
        subplot_titles=[f.replace("_", " ").title() for f in factor_names],
        horizontal_spacing=0.15,
    )
    for i, fname in enumerate(factor_names):
        levels = sorted(merged[fname].unique())
        means = [merged.loc[merged[fname] == l, response_name].mean() for l in levels]
        actual_labels = [f"{l}" for l in levels]
        fig.add_trace(
            go.Scatter(x=actual_labels, y=means, mode="lines+markers",
                       line=dict(width=2), marker=dict(size=8)),
            row=1, col=i + 1,
        )
    fig.update_layout(height=400, margin=dict(t=60, b=40), showlegend=False)
    return fig


def _build_pareto_plot(model: dict) -> go.Figure:
    """Build a Pareto chart of standardized effects."""
    coefs = [c for c in model["coefficients"] if c["term"] != "Intercept"]
    coefs.sort(key=lambda c: abs(c["estimate"]), reverse=True)

    terms = [c["term"] for c in coefs]
    estimates = [abs(c["estimate"]) for c in coefs]
    colors = ["#C4523E" if c["significant"] else "#4A90D9" for c in coefs]

    fig = go.Figure(go.Bar(
        x=estimates,
        y=terms,
        orientation="h",
        marker_color=colors,
        text=[f"{e:.3f}" for e in estimates],
        textposition="outside",
    ))
    fig.update_layout(
        title="Pareto of Effects",
        xaxis_title="|Effect Size|",
        yaxis_title="",
        height=max(300, len(terms) * 40 + 100),
        margin=dict(l=120),
        showlegend=False,
    )
    return fig


def _build_contour_plot(factors: list[dict], model: dict, response_name: str,
                         x_name: str, y_name: str) -> go.Figure:
    """Build a contour plot for two factors."""
    grid = np.linspace(-1, 1, 50)
    Z = np.zeros((50, 50))
    for i, xv in enumerate(grid):
        for j, yv in enumerate(grid):
            point = {f["name"]: 0.0 for f in factors}
            point[x_name] = xv
            point[y_name] = yv
            from doe.analysis import predict_from_model
            Z[i, j] = predict_from_model(model, factors, point)

    fig = go.Figure(go.Contour(
        z=Z, x=grid, y=grid,
        colorscale="RdYlBu_r",
        contours=dict(showlabels=True, labelfont=dict(size=10)),
    ))
    fig.update_layout(
        title=f"Contour: {response_name} — {x_name} vs {y_name}",
        xaxis_title=f"{x_name} (coded)",
        yaxis_title=f"{y_name} (coded)",
        height=500,
    )
    return fig


def _build_surface_plot(factors: list[dict], model: dict, response_name: str,
                         x_name: str, y_name: str) -> go.Figure:
    """Build a 3D response surface plot."""
    grid = np.linspace(-1, 1, 30)
    Z = np.zeros((30, 30))
    for i, xv in enumerate(grid):
        for j, yv in enumerate(grid):
            point = {f["name"]: 0.0 for f in factors}
            point[x_name] = xv
            point[y_name] = yv
            from doe.analysis import predict_from_model
            Z[i, j] = predict_from_model(model, factors, point)

    fig = go.Figure(data=[go.Surface(z=Z, x=grid, y=grid, colorscale="RdYlBu_r")])
    fig.update_layout(
        title=f"Response Surface: {response_name}",
        scene=dict(
            xaxis_title=x_name, yaxis_title=y_name, zaxis_title=response_name,
        ),
        height=500,
    )
    return fig


def _promote_to_full_factorial(session, doe_repo, factors, responses, models):
    """Promote significant factors from screening to a new full factorial DOE."""
    if not models:
        st.warning("No analysis to promote from. Run analysis first.")
        return

    # Find first response and its significant factors
    first_resp = list(models.values())[0]
    significant_terms = [
        c["term"] for c in first_resp["coefficients"]
        if c["significant"] and c["term"] != "Intercept"
        and "*" not in c["term"] and "^" not in c["term"]
    ]

    if not significant_terms:
        st.warning("No significant factors found to promote.")
        return

    # Take top 3 significant factors
    promoted_factors = [
        f for f in factors if f["name"] in significant_terms[:3]
    ]

    if not promoted_factors:
        st.warning("Could not map significant terms to factors.")
        return

    # Create new full factorial session
    sid = doe_repo.create(
        name=f"FF from screening: {session.get('name', 'DOE')}",
        entry_type="full_factorial",
        factors=promoted_factors,
        responses=responses,
    )

    st.session_state.doe_session = {
        "name": f"FF from screening: {session.get('name', 'DOE')}",
        "entry_type": "full_factorial",
        "status": "defined",
        "factors_json": promoted_factors,
        "responses_json": responses,
        "design_json": None,
        "results_json": None,
        "model_json": None,
        "optimum_json": None,
        "db_id": sid,
    }
    _go_to("define")
    st.success(f"Created new full factorial DOE with factors: "
               f"{', '.join(f['name'] for f in promoted_factors)}")
    st.rerun()
