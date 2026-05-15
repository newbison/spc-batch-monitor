import streamlit as st
from config import DATA_FILE
from data_access.repository import CsvRepository
from ui.common.sidebar import render_sidebar
from ui.operator.data_entry import render_data_entry
from ui.engineer.chart_view import render_spc_analysis
from ui.manager.dashboard import render_dashboard


def main():
    st.set_page_config(page_title="SPC App", page_icon="📊", layout="wide")

    if "repo" not in st.session_state:
        st.session_state.repo = CsvRepository(DATA_FILE)

    role, page, param = render_sidebar()

    if role == "Operator" and page == "Data Entry":
        render_data_entry(st.session_state.repo)

    elif role == "Engineer" and page == "SPC Analysis":
        render_spc_analysis(st.session_state.repo, param)

    elif role == "Manager" and page == "Dashboard":
        render_dashboard(st.session_state.repo)


if __name__ == "__main__":
    main()
