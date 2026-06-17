"""SPC sub-app sidebar — data summary and context info.

The role selector has been moved to the top of the main content area
(rendered by _render_role_bar in app.py). This sidebar now only shows
SPC-specific context: data summary and current page label.

Called by the hub (app.py) after the app-selector buttons are rendered.
"""

import streamlit as st
from data_access.base import DataRepository


def render_spc_sidebar(
    repo: DataRepository, role: str, page: str
) -> str | None:
    """Render SPC-specific sidebar content (below the hub app selector).

    Args:
        repo: data repository for summary stats
        role: currently selected role (from top bar)
        page: page name derived from role

    Returns param (for Engineer) or None.
    """
    with st.sidebar:
        # Data summary (from SQLite)
        df = repo.load_all()
        if not df.empty:
            rep_cols = [c for c in df.columns if c.startswith("rep") and c[3:].isdigit()]
            st.caption(f"{len(df)} rows  ·  {df['formula'].nunique()} formulas  "
                       f"·  {df['batch_id'].nunique()} batches  ·  {len(rep_cols)} rep cols")
        else:
            st.caption("No data loaded")

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

    return param
