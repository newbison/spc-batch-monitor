"""SPC sub-app sidebar — engineer context only.

The role selector has been moved to the top of the main content area
(rendered by _render_role_bar in app.py). The data summary and page
label have also been moved to the main content area (rendered by
_render_info_bar in app.py).

This sidebar now only shows Engineer-specific context (current
formula / parameter) so the sidebar is free for future SPC filters
and selectors.

Called by the hub (app.py) after the app-selector buttons are rendered.
"""

import streamlit as st
from data_access.base import DataRepository


def render_spc_sidebar(
    repo: DataRepository, role: str, page: str
) -> str | None:
    """Render SPC-specific sidebar content (below the hub app selector).

    Args:
        repo: data repository (unused now, kept for API compat)
        role: currently selected role (from top bar)
        page: page name derived from role

    Returns param (for Engineer) or None.
    """
    with st.sidebar:
        param = None
        if role == "Engineer":
            current_formula = st.session_state.get("eng_formula", "—")
            current_param = st.session_state.get("eng_param", "—")
            st.caption(f"Current: {current_formula} / {current_param}")
            param = st.session_state.get("eng_param", None)

    return param
