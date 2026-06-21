"""DOE (Design of Experiments) page — 2-tab Streamlit dashboard.

Tab 1: DESIGN — Setup -> Type Selection -> Diagnostics -> Run Sheet
Tab 2: ANALYZE — Data Entry -> ANOVA -> Residuals -> Profiler
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from data_access.base import DataRepository
from doe.persistence import DoeRepository
from config import DB_FILE
from doe.designs import (
    generate_full_factorial,
    generate_fractional_factorial,
    generate_box_behnken,
    generate_ccd,
    decode_to_actual,
    get_fractional_run_count,
)
from doe.analysis import fit_linear, fit_rsm, _is_center_row, anova_table, predict_from_model
from doe.optimization import optimize as doe_optimize
from doe.residuals import build_residual_plots
from doe.profiler import compute_profile, compute_overall_desirability
from doe.evaluate import evaluate_design

DOE_REPO_KEY = "doe_repo"


def _get_doe_repo() -> DoeRepository:
    if DOE_REPO_KEY not in st.session_state:
        st.session_state[DOE_REPO_KEY] = DoeRepository(DB_FILE)
    return st.session_state[DOE_REPO_KEY]


def render_doe_page(repo: DataRepository):
    doe_repo = _get_doe_repo()

    # Init state
    if "doe_active_tab" not in st.session_state:
        st.session_state.doe_active_tab = "design"
    if "doe_session" not in st.session_state:
        st.session_state.doe_session = None
    if "doe_session_id" not in st.session_state:
        st.session_state.doe_session_id = None

    # --- Sidebar ---
    with st.sidebar:
        st.markdown('<p class="sidebar-section-label">DOE SESSION</p>', unsafe_allow_html=True)

        # Tab buttons
        c1, c2 = st.columns(2)
        with c1:
            if st.button("📐  DESIGN", use_container_width=True,
                         type="primary" if st.session_state.doe_active_tab == "design" else "secondary",
                         key="doe_tab_design"):
                st.session_state.doe_active_tab = "design"
                st.rerun()
        with c2:
            if st.button("📊  ANALYZE", use_container_width=True,
                         type="primary" if st.session_state.doe_active_tab == "analyze" else "secondary",
                         key="doe_tab_analyze"):
                st.session_state.doe_active_tab = "analyze"
                st.rerun()

        # Session info
        session = st.session_state.doe_session
        if session:
            st.caption(f"Name: {session.get('name', 'Untitled')}")
            st.caption(f"Type: {session.get('entry_type', '—').replace('_', ' ').title()}")
            st.divider()
            if st.button("➕  New DOE", use_container_width=True):
                _reset_doe()
        else:
            st.caption("No active session")

        # Saved sessions
        saved = doe_repo.list_sessions()
        if saved:
            st.divider()
            st.markdown('<p class="sidebar-section-label">SAVED SESSIONS</p>', unsafe_allow_html=True)
            status_icon = {"defined": "⚪", "designed": "🔵", "running": "🟡", "analyzed": "🟢", "optimized": "✅"}
            for s in saved[:8]:
                icon = status_icon.get(s["status"], "⚪")
                label = f"{icon} {s['name'][:28]}"
                if st.button(label, key=f"doe_load_{s['id']}", use_container_width=True,
                             help=f"Status: {s['status']}  |  Type: {s['entry_type']}\nClick to load this session"):
                    _load_session(doe_repo, s["id"])

    # --- Main content ---
    st.title("Design of Experiments")

    if st.session_state.doe_active_tab == "design":
        _render_design_tab(doe_repo)
    else:
        _render_analyze_tab(doe_repo)


# ---------------------------------------------------------------------------
# Tab 1: DESIGN
# ---------------------------------------------------------------------------

def _render_design_tab(doe_repo: DoeRepository):
    session = st.session_state.doe_session

    # If no session, show landing
    if session is None:
        _render_landing(doe_repo)
        return

    factors = session.get("factors_json", [])
    responses = session.get("responses_json", [])
    design_exists = session.get("design_json") is not None

    # -- Section 1: Setup --
    with st.expander("SETUP: Factors & Responses", expanded=not design_exists):
        _render_setup_section(session)

    if not factors or not responses:
        st.info("Define at least one factor and one response above to continue.")
        return

    # -- Section 2: Design Type --
    with st.expander("DESIGN TYPE", expanded=not design_exists):
        design_type = st.radio(
            "Select design type",
            options=["full_factorial", "fractional_factorial", "ccd", "box_behnken"],
            format_func=lambda x: {
                "full_factorial": "Full Factorial (2^k)",
                "fractional_factorial": "Fractional Factorial (2^(k-p))",
                "ccd": "Central Composite Design (CCD)",
                "box_behnken": "Box-Behnken",
            }[x],
            horizontal=True,
            key="doe_design_type",
        )

        col1, col2 = st.columns(2)
        with col1:
            n_center = st.slider("Center points", 0, 5, 3, key="doe_n_center")
        with col2:
            if design_type == "fractional_factorial":
                resolution = st.selectbox("Resolution", [4, 5], index=0, key="doe_resolution")
            elif design_type == "ccd":
                alpha = st.selectbox("Alpha", ["rotatable", "face-centered", "orthogonal"],
                                     index=0, key="doe_ccd_alpha")

        # Run count estimate
        k = len([f for f in factors if f["type"] == "continuous"])
        if design_type == "full_factorial":
            n_runs = 2 ** k + n_center
        elif design_type == "fractional_factorial":
            n_runs = get_fractional_run_count(k, resolution) + n_center
        elif design_type == "ccd":
            n_runs = 2 ** k + 2 * k + n_center
        else:  # BB
            n_runs = len(generate_box_behnken(factors, n_center=n_center))
        st.info(f"Estimated runs: **{n_runs}** ({2**k} factorial + rest)")

        if st.button("Generate Design", type="primary", key="doe_gen_design"):
            if design_type == "full_factorial":
                coded_df = generate_full_factorial(factors, n_center=n_center)
            elif design_type == "fractional_factorial":
                coded_df = generate_fractional_factorial(factors, resolution=resolution)
            elif design_type == "ccd":
                coded_df = generate_ccd(factors, alpha=alpha, n_center=n_center)
            else:
                coded_df = generate_box_behnken(factors, n_center=n_center)

            session["design_json"] = coded_df.to_dict("records")
            session["design_type"] = design_type

            if session.get("db_id"):
                doe_repo.update(session["db_id"], {
                    "design": coded_df.to_dict("records"),
                    "entry_type": design_type,
                    "status": "designed",
                })
            st.rerun()

    if not design_exists:
        return

    design_df = pd.DataFrame(session["design_json"])
    decoded_df = decode_to_actual(design_df, factors)

    # -- Section 3: Diagnostics --
    with st.expander("DESIGN DIAGNOSTICS"):
        if st.button("Evaluate Design", key="doe_evaluate"):
            diag = evaluate_design(design_df, factors, model_order="linear")

            c1, c2, c3 = st.columns(3)
            with c1:
                power_1s = diag["power"].get(1.0, 0)
                color = "normal" if power_1s >= 0.8 else "off"
                st.metric("Power (1sigma effect)", f"{power_1s:.2f}",
                          delta="Good" if power_1s >= 0.8 else "Low",
                          delta_color=color)
            with c2:
                max_vif = max(diag["vif"].values()) if diag["vif"] else 1.0
                st.metric("Max VIF", f"{max_vif:.2f}",
                          delta="OK" if max_vif < 5 else "High",
                          delta_color="normal" if max_vif < 5 else "off")
            with c3:
                st.metric("G-Efficiency", f"{diag['g_efficiency']:.2f}")

            for w in diag.get("warnings", []):
                st.warning(w)

    # -- Section 4: Run Sheet --
    with st.expander("RUN SHEET", expanded=True):
        st.dataframe(decoded_df, use_container_width=True, hide_index=True)

        # Download
        response_names = [r["name"] for r in responses]
        dl_df = decoded_df.copy()
        for rname in response_names:
            dl_df[rname] = ""
        csv_data = dl_df.to_csv(index=False)
        st.download_button("Download Run Sheet (CSV)", csv_data,
                           file_name=f"doe_{session.get('name', 'design')}.csv",
                           mime="text/csv", key="doe_dl_design")

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("New DOE", key="doe_design_new"):
            _reset_doe()
    with c2:
        if st.button("Go to Analyze ->", type="primary", key="doe_to_analyze"):
            st.session_state.doe_active_tab = "analyze"
            st.rerun()


# ---------------------------------------------------------------------------
# Tab 2: ANALYZE
# ---------------------------------------------------------------------------

def _render_analyze_tab(doe_repo: DoeRepository):
    session = st.session_state.doe_session

    if session is None or session.get("design_json") is None:
        st.info("Generate a design first (DESIGN tab) before analyzing.")
        if st.button("Go to DESIGN tab"):
            st.session_state.doe_active_tab = "design"
            st.rerun()
        return

    design_df = pd.DataFrame(session["design_json"])
    factors = session.get("factors_json", [])
    responses = session.get("responses_json", [])
    response_names = [r["name"] for r in responses]
    db_id = session.get("db_id")

    # -- Section 1: Data Entry --
    results_exist = session.get("results_json") is not None

    with st.expander("DATA ENTRY", expanded=not results_exist):
        uploaded = st.file_uploader("Upload completed run sheet CSV", type=["csv"], key="doe_upload_results")
        if uploaded:
            try:
                uploaded_df = pd.read_csv(uploaded)
                # Validate required columns
                missing_cols = [rname for rname in response_names if rname not in uploaded_df.columns]
                if missing_cols:
                    st.error(f"Missing response columns: {', '.join(missing_cols)}")
                    return

                # Validate every cell
                errors = []
                results = []
                for idx, row in uploaded_df.iterrows():
                    run_num = int(row["run"])
                    run_result = {"run": run_num}
                    for rname in response_names:
                        val = row[rname]
                        if pd.isna(val):
                            errors.append(f"Run {run_num}: '{rname}' is empty")
                        else:
                            try:
                                run_result[rname] = float(val)
                            except (ValueError, TypeError):
                                errors.append(f"Run {run_num}: '{rname}' = '{val}' is not a number")
                    results.append(run_result)

                if errors:
                    st.error(f"Found {len(errors)} issue(s) in the uploaded data:")
                    for err in errors[:10]:
                        st.write(f"- {err}")
                    if len(errors) > 10:
                        st.write(f"- ... and {len(errors) - 10} more")
                    return

                session["results_json"] = results
                if db_id:
                    doe_repo.update(db_id, {"results": results, "status": "running"})
                st.success(f"Loaded {len(results)} runs with {len(response_names)} responses — all valid ✓")
                st.rerun()
            except Exception as e:
                st.error(f"Error reading CSV: {e}")

        # Manual entry fallback
        if not results_exist and not uploaded:
            st.caption("Or enter data below after generating the design.")

    if not results_exist:
        return

    results_df = pd.DataFrame(session["results_json"])

    # -- Section 2: Analysis --
    if "doe_analysis_results" not in st.session_state:
        st.session_state.doe_analysis_results = None

    if st.button("Run Analysis", type="primary", key="doe_run_analysis"):
        analysis_results = {}
        for r in responses:
            rname = r["name"]
            # Try RSM first if center points exist, else linear
            is_center = _is_center_row(design_df, [f["name"] for f in factors])
            if is_center.sum() >= 3:
                model = fit_rsm(factors, design_df, results_df, rname)
            else:
                model = fit_linear(factors, design_df, results_df, rname)
            analysis_results[rname] = model
        st.session_state.doe_analysis_results = analysis_results
        if db_id:
            doe_repo.update(db_id, {"analysis": analysis_results, "status": "analyzed"})
        st.rerun()

    analysis = st.session_state.doe_analysis_results
    if analysis is None:
        return

    # -- Section 3: ANOVA --
    with st.expander("ANOVA TABLE", expanded=True):
        for rname in response_names:
            if rname not in analysis:
                continue
            model = analysis[rname]
            st.markdown(f"**Response: {rname}**")
            anova_df = anova_table(model)
            st.dataframe(anova_df, use_container_width=True, hide_index=True)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("R²", f"{model.get('r_squared', 0):.4f}")
            c2.metric("Adj R²", f"{model.get('r_squared_adj', 0):.4f}")
            c3.metric("RMSE", f"{model.get('rmse', 0):.4f}")
            lof_p = model.get("lack_of_fit_p")
            c4.metric("Lack-of-fit p", f"{lof_p:.4f}" if lof_p is not None else "N/A")
            st.divider()

    # -- Section 4: Residuals --
    with st.expander("RESIDUAL DIAGNOSTICS"):
        for rname in response_names:
            if rname not in analysis:
                continue
            model = analysis[rname]
            resid_data = model.get("residuals", {})
            if not resid_data:
                st.caption(f"No residual data for {rname}")
                continue

            st.markdown(f"**{rname}**")
            resid_dict = {
                "residuals": np.array(resid_data.get("residual", [])),
                "studentized": np.array([v if v is not None else float('nan') for v in resid_data.get("studentized", [])]),
                "predicted": np.array(resid_data.get("predicted", [])),
                "run_order": np.array(resid_data.get("run", [])),
                "leverage": np.array([v if v is not None else 0.0 for v in resid_data.get("leverage", [])]),
                "cooks_d": np.array([v if v is not None else 0.0 for v in resid_data.get("cooks_d", [])]) if resid_data.get("cooks_d") else np.zeros(len(resid_data.get("residual", []))),
                "shapiro_p": None,
            }

            fig = build_residual_plots(resid_dict)
            st.plotly_chart(fig, use_container_width=True)
            st.divider()

    # -- Section 5: Effects & Plots --
    with st.expander("EFFECTS & PLOTS"):
        factor_names = [f["name"] for f in factors]
        merged = design_df.merge(results_df, on="run") if not results_df.empty else design_df.copy()

        for rname in response_names:
            if rname not in analysis or rname not in merged.columns:
                continue
            model = analysis[rname]
            st.markdown(f"**{rname}**")

            # Pareto
            coefs = [c for c in model["coefficients"] if c["term"] != "Intercept"]
            coefs.sort(key=lambda c: abs(c["estimate"]), reverse=True)
            pareto_fig = go.Figure(go.Bar(
                x=[abs(c["estimate"]) for c in coefs],
                y=[c["term"] for c in coefs],
                orientation="h",
                marker_color=["#C4523E" if c["significant"] else "#4A90D9" for c in coefs],
                text=[f"{abs(c['estimate']):.3f}" for c in coefs],
                textposition="outside",
            ))
            pareto_fig.update_layout(
                title=f"Pareto of Effects — {rname}",
                height=max(300, len(coefs) * 40 + 100),
                margin=dict(l=120),
                showlegend=False,
            )
            st.plotly_chart(pareto_fig, use_container_width=True)

            # Main effects
            if factor_names:
                fig_me = make_subplots(rows=1, cols=len(factor_names),
                                       subplot_titles=factor_names)
                for i, fn in enumerate(factor_names):
                    levels = sorted(merged[fn].unique())
                    means = [merged.loc[merged[fn] == l, rname].mean() for l in levels]
                    fig_me.add_trace(go.Scatter(x=[str(l) for l in levels], y=means,
                                                mode="lines+markers"), row=1, col=i+1)
                fig_me.update_layout(height=300, showlegend=False)
                st.plotly_chart(fig_me, use_container_width=True)

            # Contour + surface for RSM models with 2+ continuous factors
            cont_factors_rsm = [f for f in factors if f["type"] == "continuous"]
            is_rsm = any(c["term"].endswith("^2") for c in model.get("coefficients", []))
            if is_rsm and len(cont_factors_rsm) >= 2:
                x_name = cont_factors_rsm[0]["name"]
                y_name = cont_factors_rsm[1]["name"]
                st.markdown(f"*Response surface: {x_name} × {y_name}*")

                c_col1, c_col2 = st.columns(2)
                with c_col1:
                    # Contour plot
                    grid = np.linspace(-1, 1, 50)
                    Z = np.zeros((50, 50))
                    for gi, xv in enumerate(grid):
                        for gj, yv in enumerate(grid):
                            point = {f["name"]: 0.0 for f in factors}
                            point[x_name] = xv
                            point[y_name] = yv
                            Z[gi, gj] = predict_from_model(model, factors, point)
                    contour_fig = go.Figure(go.Contour(
                        z=Z, x=grid, y=grid,
                        colorscale="RdYlBu_r",
                        contours=dict(showlabels=True, labelfont=dict(size=10)),
                    ))
                    contour_fig.update_layout(
                        title=f"Contour: {rname}",
                        xaxis_title=f"{x_name} (coded)",
                        yaxis_title=f"{y_name} (coded)",
                        height=400,
                    )
                    st.plotly_chart(contour_fig, use_container_width=True)
                with c_col2:
                    # 3D surface plot
                    grid_3d = np.linspace(-1, 1, 30)
                    Z_3d = np.zeros((30, 30))
                    for gi, xv in enumerate(grid_3d):
                        for gj, yv in enumerate(grid_3d):
                            point = {f["name"]: 0.0 for f in factors}
                            point[x_name] = xv
                            point[y_name] = yv
                            Z_3d[gi, gj] = predict_from_model(model, factors, point)
                    surface_fig = go.Figure(data=[go.Surface(
                        z=Z_3d, x=grid_3d, y=grid_3d, colorscale="RdYlBu_r"
                    )])
                    surface_fig.update_layout(
                        title=f"Surface: {rname}",
                        scene=dict(
                            xaxis_title=x_name, yaxis_title=y_name,
                            zaxis_title=rname,
                        ),
                        height=400,
                    )
                    st.plotly_chart(surface_fig, use_container_width=True)

    # -- Section 6: Prediction Profiler --
    with st.expander("PREDICTION PROFILER", expanded=True):
        if "doe_profiler_positions" not in st.session_state:
            st.session_state.doe_profiler_positions = {
                f["name"]: 0.0 for f in factors if f["type"] == "continuous"
            }

        positions = st.session_state.doe_profiler_positions

        # Factor sliders
        cont_factors = [f for f in factors if f["type"] == "continuous"]
        if cont_factors:
            slider_cols = st.columns(min(len(cont_factors), 6))
            for i, f in enumerate(cont_factors):
                col_idx = i % len(slider_cols)
                with slider_cols[col_idx]:
                    positions[f["name"]] = st.slider(
                        f["name"], -1.0, 1.0, positions.get(f["name"], 0.0),
                        0.01, key=f"prof_slider_{f['name']}"
                    )
        else:
            st.info("No continuous factors for profiling.")
            return

        # Compute profile
        profile = compute_profile(factors, analysis, responses, positions)

        # Response trace columns
        resp_cols = st.columns(min(len(responses), 4))
        for i, r in enumerate(responses):
            rname = r["name"]
            if rname not in profile:
                continue
            col_idx = i % len(resp_cols)
            with resp_cols[col_idx]:
                p = profile[rname]
                st.metric(rname, f"{p['predicted']:.3f}")
                d = p["desirability"]
                d_color = "#00BFA5" if d >= 0.7 else "#F39C12" if d >= 0.3 else "#C4523E"
                st.markdown(
                    f"<span style='color:{d_color};font-weight:700'>D = {d:.3f}</span>",
                    unsafe_allow_html=True,
                )
                st.progress(d)

                # Mini trace plot for first continuous factor
                for fn_dict in cont_factors[:1]:
                    fn_name = fn_dict["name"]
                    if fn_name in p["traces"]:
                        trace = p["traces"][fn_name]
                        tf = go.Figure(go.Scatter(x=trace["x"], y=trace["y"], mode="lines",
                                                   line=dict(width=2, color="#C4734F")))
                        tf.update_layout(height=100, margin=dict(l=0, r=0, t=0, b=0))
                        st.plotly_chart(tf, use_container_width=True, config={"displayModeBar": False})

        # Overall desirability
        ind_d = [profile[r["name"]]["desirability"] for r in responses if r["name"] in profile]
        overall_d = compute_overall_desirability(ind_d) if ind_d else 0.0

        col_od, col_opt = st.columns([2, 1])
        with col_od:
            st.metric("Overall Desirability", f"D = {overall_d:.3f}")
            if overall_d >= 0.8:
                st.success("Excellent")
            elif overall_d >= 0.5:
                st.warning("Acceptable")
            else:
                st.error("Poor - adjust goals")

        with col_opt:
            if st.button("Find Optimum", type="primary", key="doe_find_opt"):
                result = doe_optimize(factors, responses, analysis, n_starts=10)
                # Update slider positions
                for f in factors:
                    if f["type"] != "continuous":
                        continue
                    opt_val = result["optimal_settings"].get(f["name"])
                    if opt_val is not None:
                        coded = (2 * (opt_val - f["low"]) / (f["high"] - f["low"])) - 1
                        positions[f["name"]] = float(max(-1.0, min(1.0, coded)))
                st.session_state.doe_profiler_positions = positions
                st.rerun()

    st.divider()
    if st.button("New DOE", key="doe_analyze_new"):
        _reset_doe()


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _render_landing(doe_repo: DoeRepository):
    """New DOE landing."""
    st.subheader("Start a New DOE")

    entry_type = st.radio(
        "Design type",
        options=["full_factorial", "fractional_factorial", "ccd", "box_behnken"],
        format_func=lambda x: {
            "full_factorial": "Full Factorial - characterize known critical factors (2^k)",
            "fractional_factorial": "Fractional Factorial - screen many factors with few runs",
            "ccd": "Central Composite - RSM with 5 levels per factor",
            "box_behnken": "Box-Behnken - RSM with 3 levels, fewer runs than CCD",
        }[x],
        key="doe_new_entry_type",
    )
    name = st.text_input("DOE Name", placeholder="e.g., Formulation Optimization #3", key="doe_new_name")

    if st.button("Start", type="primary", key="doe_new_start"):
        session = {
            "name": name or "Untitled DOE",
            "entry_type": entry_type,
            "status": "defined",
            "factors_json": [],
            "responses_json": [],
            "design_json": None,
            "results_json": None,
            "analysis_json": None,
            "optimum_json": None,
            "design_type": None,
        }
        st.session_state.doe_session = session

        # Save to DB
        sid = doe_repo.create(
            name=session["name"],
            entry_type=entry_type,
            factors=[],
            responses=[],
        )
        session["db_id"] = sid
        st.session_state.doe_session_id = sid
        st.rerun()


def _render_setup_section(session: dict):
    """Factor and response definition (inline editors).

    Continuous factors: optional low/high bounds (any numeric value).
    Categorical factors: named levels (e.g. A, B, C...) via text inputs.
    """
    # ---- Factors ----
    st.markdown("**Factors**")
    if "doe_factors_list" not in st.session_state:
        existing = session.get("factors_json", [])
        st.session_state.doe_factors_list = existing if existing else [
            {"name": "", "type": "continuous", "low": 0.0, "high": 1.0}
        ]

    for i, row in enumerate(st.session_state.doe_factors_list):
        is_cat = row.get("type") == "categorical"

        if is_cat:
            # One compact line: name | type ▼ | level inputs... | +level | ✕
            if "levels" not in row or not row["levels"]:
                row["levels"] = ["A", "B"]
            n_levels = len(row["levels"])
            # Dynamic columns: name(2) + type(1.5) + one per level(each 1.5) + add(0.5) + del(0.5)
            cols = st.columns([2.5, 1.5] + [1.5] * n_levels + [0.5, 0.5])
            with cols[0]:
                row["name"] = st.text_input("Name", row.get("name", ""), key=f"fac_n_{i}",
                                            label_visibility="collapsed", placeholder=f"Factor {i+1}")
            with cols[1]:
                row["type"] = st.selectbox("Type", ["continuous", "categorical"],
                                           index=1, key=f"fac_t_{i}", label_visibility="collapsed")
            for li in range(n_levels):
                with cols[2 + li]:
                    row["levels"][li] = st.text_input(
                        f"Lv{li+1}", row["levels"][li], key=f"fac_lev_{i}_{li}",
                        label_visibility="collapsed", placeholder=f"Level {li+1}",
                    )
            with cols[2 + n_levels]:
                if st.button("+", key=f"fac_addlev_{i}", help="Add level"):
                    row["levels"].append("")
                    st.rerun()
            with cols[2 + n_levels + 1]:
                if len(st.session_state.doe_factors_list) > 1:
                    if st.button("✕", key=f"fac_del_{i}", help="Remove factor"):
                        st.session_state.doe_factors_list.pop(i)
                        st.rerun()
        else:
            # One compact line: name | type ▼ | low | high | ✕
            c1, c2, c3, c4, c5 = st.columns([2.5, 1.5, 1.5, 1.5, 0.5])
            with c1:
                row["name"] = st.text_input("Name", row.get("name", ""), key=f"fac_n_{i}",
                                            label_visibility="collapsed", placeholder=f"Factor {i+1}")
            with c2:
                row["type"] = st.selectbox("Type", ["continuous", "categorical"],
                                           index=0, key=f"fac_t_{i}", label_visibility="collapsed")
            with c3:
                low_val = row.get("low")
                row["low"] = st.number_input("Low", value=float(low_val) if low_val is not None else 0.0,
                                             key=f"fac_l_{i}", label_visibility="collapsed",
                                             step=0.01, format="%.4f")
            with c4:
                high_val = row.get("high")
                row["high"] = st.number_input("High", value=float(high_val) if high_val is not None else 1.0,
                                              key=f"fac_h_{i}", label_visibility="collapsed",
                                              step=0.01, format="%.4f")
            with c5:
                if len(st.session_state.doe_factors_list) > 1:
                    if st.button("✕", key=f"fac_del_{i}", help="Remove factor"):
                        st.session_state.doe_factors_list.pop(i)
                        st.rerun()

    if st.button("+ Add Factor", key="doe_add_f"):
        st.session_state.doe_factors_list.append(
            {"name": "", "type": "continuous", "low": 0.0, "high": 1.0}
        )
        st.rerun()

    # ---- Responses ----
    st.markdown("**Responses**")
    if "doe_responses_list" not in st.session_state:
        existing = session.get("responses_json", [])
        st.session_state.doe_responses_list = existing if existing else [
            {"name": "", "goal": "maximize", "target": None, "low": 0.0, "high": 1.0}
        ]

    for i, row in enumerate(st.session_state.doe_responses_list):
        goal = row.get("goal", "maximize")
        c1, c2, c3, c4, c5, c6 = st.columns([3, 1.3, 1.3, 1.3, 1.3, 0.8])
        with c1:
            row["name"] = st.text_input("Name", row.get("name", ""), key=f"resp_n_{i}",
                                        label_visibility="collapsed", placeholder=f"Response {i+1}")
        with c2:
            row["goal"] = st.selectbox("Goal", ["maximize", "minimize", "target"],
                                       index=["maximize","minimize","target"].index(goal) if goal in ["maximize","minimize","target"] else 0,
                                       key=f"resp_g_{i}", label_visibility="collapsed")
        with c3:
            if goal in ("maximize", "target"):
                row["low"] = st.number_input("Min acceptable", float(row.get("low", 0)),
                                             key=f"resp_l_{i}", label_visibility="collapsed",
                                             step=0.01, format="%.4f",
                                             help="Minimum acceptable value")
            else:
                st.caption("")
        with c4:
            if goal in ("minimize", "target"):
                row["high"] = st.number_input("Max acceptable", float(row.get("high", 1)),
                                              key=f"resp_h_{i}", label_visibility="collapsed",
                                              step=0.01, format="%.4f",
                                              help="Maximum acceptable value")
            else:
                st.caption("")
        with c5:
            if goal == "target":
                row["target"] = st.number_input("Target", float(row.get("target") or row.get("low", 0)),
                                                key=f"resp_t_{i}", label_visibility="collapsed",
                                                step=0.01, format="%.4f",
                                                help="Ideal target value")
            else:
                st.caption("")
        with c6:
            if len(st.session_state.doe_responses_list) > 1:
                if st.button("✕", key=f"resp_del_{i}"):
                    st.session_state.doe_responses_list.pop(i)
                    st.rerun()

    if st.button("+ Add Response", key="doe_add_r"):
        st.session_state.doe_responses_list.append(
            {"name": "", "goal": "maximize", "target": None, "low": 0.0, "high": 1.0}
        )
        st.rerun()

    # Save to session
    valid_factors = [f for f in st.session_state.doe_factors_list if f.get("name") and str(f["name"]).strip()]
    valid_responses = [r for r in st.session_state.doe_responses_list if r.get("name") and str(r["name"]).strip()]
    session["factors_json"] = valid_factors
    session["responses_json"] = valid_responses


def _reset_doe():
    st.session_state.doe_step = "landing"  # compat
    st.session_state.doe_session = None
    st.session_state.doe_session_id = None
    st.session_state.doe_analysis_results = None
    st.session_state.doe_profiler_positions = None
    st.session_state.doe_active_tab = "design"
    st.rerun()


def _load_session(doe_repo: DoeRepository, sid: int):
    try:
        s = doe_repo.load(sid)
        # Backward compat: old sessions used 'model' column; new sessions use 'analysis'
        analysis_data = s.get("analysis") or s.get("model")
        optimum_data = s.get("optimum")
        st.session_state.doe_session = {
            "name": s["name"],
            "entry_type": s["entry_type"],
            "status": s["status"],
            "factors_json": s["factors"] if s["factors"] else [],
            "responses_json": s["responses"] if s["responses"] else [],
            "design_json": s.get("design"),
            "results_json": s.get("results"),
            "analysis_json": analysis_data,
            "optimum_json": optimum_data,
            "db_id": sid,
        }
        st.session_state.doe_session_id = sid
        st.session_state.doe_analysis_results = analysis_data

        # Restore profiler slider positions from optimum if available
        if optimum_data and optimum_data.get("optimal_settings"):
            factors = s.get("factors", [])
            positions = {}
            for f in factors:
                if f.get("type") != "continuous":
                    continue
                opt_val = optimum_data["optimal_settings"].get(f["name"])
                if opt_val is not None and f.get("low") != f.get("high"):
                    coded = (2 * (opt_val - f["low"]) / (f["high"] - f["low"])) - 1
                    positions[f["name"]] = float(max(-1.0, min(1.0, coded)))
                else:
                    positions[f["name"]] = 0.0
            if positions:
                st.session_state.doe_profiler_positions = positions

        # Route to appropriate tab based on session status
        status = s.get("status", "defined")
        if status in ("analyzed", "optimized") and s.get("results"):
            st.session_state.doe_active_tab = "analyze"
        elif status == "designed" or s.get("design"):
            st.session_state.doe_active_tab = "design"
        else:
            st.session_state.doe_active_tab = "design"
        st.rerun()
    except KeyError:
        st.error(f"Session {sid} not found.")
