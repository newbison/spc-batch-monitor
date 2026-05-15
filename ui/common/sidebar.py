import streamlit as st
import pandas as pd
from config import DATA_FILE, SUBGROUP_SIZE

ROLES = ["Operator", "Engineer", "Manager"]


def render_sidebar() -> tuple[str, str, str | None]:
    with st.sidebar:
        st.title("📊 SPC App")
        st.caption("Statistical Process Control")

        role = st.selectbox("Role", ROLES, key="role_selector")

        st.divider()

        # Data summary
        params_list = []
        if DATA_FILE.exists():
            df = pd.read_csv(DATA_FILE)
            params_list = sorted(df["parameter"].unique().tolist())
            rep_cols = [c for c in df.columns if c.startswith("rep")]
            n_reps = len(rep_cols)
            st.caption(f"{len(df)} rows | {df['formula'].nunique()} formulas "
                       f"| {df['batch_id'].nunique()} batches | n={n_reps}")
        else:
            st.caption("No data loaded")

        st.divider()
        st.caption(f"Logged in as: **{role}**")

        page = None
        if role == "Operator":
            page = st.radio("Page", ["Data Entry"], label_visibility="collapsed")
        elif role == "Engineer":
            page = st.radio("Page", ["SPC Analysis"], label_visibility="collapsed")
        elif role == "Manager":
            page = st.radio("Page", ["Dashboard"], label_visibility="collapsed")

        # Parameter selector (only shown for engineer, hidden for operator/manager)
        param = None
        if role == "Engineer":
            st.divider()
            if params_list:
                param = st.selectbox("Parameter", params_list)
            else:
                param = st.selectbox("Parameter", ["—"])

    return role, page, param
