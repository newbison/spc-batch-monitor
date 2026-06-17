"""SPC sub-app sidebar — role selector, data summary, current page label.

Called by the hub (app.py) after the app-selector buttons are rendered.
"""

import streamlit as st
from data_access.base import DataRepository

ROLES = ["Operator", "Engineer", "Manager", "Admin"]

# Each role maps to exactly one SPC page (DOE is now a separate app).
PAGE_MAP = {
    "Operator": "Data Entry",
    "Engineer": "SPC Analysis",
    "Manager": "Dashboard",
    "Admin": "Data Management",
}


def render_spc_sidebar(repo: DataRepository) -> tuple[str, str, str | None]:
    """Render SPC-specific sidebar content (below the hub app selector).

    Returns (role, page, param).
    """
    with st.sidebar:
        role = st.selectbox("Role", ROLES, key="role_selector")

        st.divider()

        # Data summary (from SQLite)
        df = repo.load_all()
        if not df.empty:
            rep_cols = [c for c in df.columns if c.startswith("rep") and c[3:].isdigit()]
            st.caption(f"{len(df)} rows  ·  {df['formula'].nunique()} formulas  "
                       f"·  {df['batch_id'].nunique()} batches  ·  {len(rep_cols)} rep cols")
        else:
            st.caption("No data loaded")

        page = PAGE_MAP.get(role, "Data Entry")

        # Show current page as a label
        st.divider()
        st.markdown(
            f'<p class="sidebar-section-label">{page.upper()}</p>',
            unsafe_allow_html=True,
        )

        # Engineer: show current formula/param
        param = None
        if role == "Engineer":
            current_formula = st.session_state.get("eng_formula", "—")
            current_param = st.session_state.get("eng_param", "—")
            st.caption(f"Current: {current_formula} / {current_param}")
            param = st.session_state.get("eng_param", None)

    return role, page, param
