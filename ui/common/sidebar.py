import streamlit as st
from data_access.base import DataRepository

ROLES = ["Operator", "Engineer", "Manager", "Admin"]


def render_sidebar(repo: DataRepository) -> tuple[str, str, str | None]:
    with st.sidebar:
        st.markdown("""
        <div class="sidebar-header">
            <h1>SPC App</h1>
            <p>Statistical Process Control</p>
        </div>
        """, unsafe_allow_html=True)

        role = st.selectbox("Role", ROLES, key="role_selector")

        st.divider()

        # Data summary (from SQLite, not CSV)
        df = repo.load_all()
        if not df.empty:
            rep_cols = [c for c in df.columns if c.startswith("rep") and c[3:].isdigit()]
            st.caption(f"{len(df)} rows  ·  {df['formula'].nunique()} formulas  "
                       f"·  {df['batch_id'].nunique()} batches  ·  {len(rep_cols)} rep cols")
        else:
            st.caption("No data loaded")

        page = None
        if role == "Operator":
            page = st.radio("Page", ["Data Entry"], label_visibility="collapsed")
        elif role == "Engineer":
            page = _render_engineer_nav()
        elif role == "Manager":
            page = st.radio("Page", ["Dashboard"], label_visibility="collapsed")
        elif role == "Admin":
            page = st.radio("Page", ["Data Management"], label_visibility="collapsed")

        # Parameter read from session state (set by engineer page selector)
        param = None
        if role == "Engineer":
            st.divider()
            current_formula = st.session_state.get("eng_formula", "—")
            current_param = st.session_state.get("eng_param", "—")
            st.caption(f"Current: {current_formula} / {current_param}")
            param = st.session_state.get("eng_param", None)

    return role, page, param


def _render_engineer_nav() -> str:
    """Render visually distinct Engineer navigation with prominent DOE entry.

    SPC Analysis is shown as a standard navigation item.  DOE is shown as a
    highlighted call-to-action button that stands out in the dark sidebar.
    Session state tracks the active page so the selection persists across
    re-runs.
    """
    # Initialize page state
    if "eng_active_page" not in st.session_state:
        st.session_state.eng_active_page = "SPC Analysis"

    st.divider()

    # --- SPC Analysis ---
    spc_active = st.session_state.eng_active_page == "SPC Analysis"
    spc_label = "📈  SPC Analysis" if spc_active else "SPC Analysis"
    if st.button(
        spc_label,
        use_container_width=True,
        type="primary" if spc_active else "secondary",
        key="eng_nav_spc",
    ):
        st.session_state.eng_active_page = "SPC Analysis"
        st.rerun()

    # --- DOE — prominent call-to-action ---
    st.markdown(
        '<p class="doe-sidebar-label">DESIGN OF EXPERIMENTS</p>',
        unsafe_allow_html=True,
    )
    doe_active = st.session_state.eng_active_page == "DOE"
    doe_label = "🔬  DOE Wizard" if doe_active else "🔬  Open DOE Wizard"
    if st.button(
        doe_label,
        use_container_width=True,
        type="primary",
        key="eng_nav_doe",
    ):
        st.session_state.eng_active_page = "DOE"
        st.rerun()

    return st.session_state.eng_active_page
