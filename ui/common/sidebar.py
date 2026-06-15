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
            page = st.radio("Page", ["SPC Analysis", "DOE"], label_visibility="collapsed")
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
