import streamlit as st
from config import DB_FILE
from data_access.sqlite_repository import SqliteRepository
from ui.common.sidebar import render_sidebar
from ui.operator.data_entry import render_data_entry
from ui.engineer.chart_view import render_spc_analysis
from ui.manager.dashboard import render_dashboard

CUSTOM_CSS = """
<style>
    /* Hide Streamlit chrome */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stApp {background: #F8FAFC;}

    /* --- Sidebar --- */
    section[data-testid="stSidebar"] > div:first-child {padding-top: 0;}
    section[data-testid="stSidebar"] .sidebar-header {
        background: linear-gradient(135deg, #0D7377, #14A3A8);
        padding: 1.2rem 1rem 0.8rem 1rem;
        margin: 0 -1rem 1rem -1rem;
        color: white;
        border-radius: 0;
    }
    section[data-testid="stSidebar"] .sidebar-header h1 {
        color: white; font-size: 1.3rem; margin: 0; font-weight: 700;
    }
    section[data-testid="stSidebar"] .sidebar-header p {
        color: rgba(255,255,255,0.8); font-size: 0.8rem; margin: 0.2rem 0 0 0;
    }
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stRadio label {
        font-size: 0.8rem; color: #64748B; font-weight: 600;
    }

    /* --- Metric cards --- */
    div[data-testid="stMetric"] {
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    div[data-testid="stMetric"] > div:first-child {gap: 0;}
    div[data-testid="stMetricLabel"] {
        font-size: 0.75rem; color: #64748B; font-weight: 600;
        text-transform: uppercase; letter-spacing: 0.03em;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.5rem; font-weight: 700; color: #1E293B;
    }

    /* --- Buttons --- */
    button[kind="primary"] {
        border-radius: 6px; font-weight: 600;
        transition: all 0.15s ease;
    }
    button[kind="primary"]:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(13,115,119,0.3);
    }

    /* --- Expanders --- */
    div[data-testid="stExpander"] {
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        background: white;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    div[data-testid="stExpander"] > details > summary > span {
        font-weight: 600; font-size: 0.9rem;
    }

    /* --- DataFrames --- */
    div[data-testid="stDataFrame"] {
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }

    /* --- Alerts --- */
    .stAlert {
        border-radius: 6px; border-left-width: 4px;
        font-size: 0.9rem;
    }

    /* --- Typography --- */
    h1 {font-size: 1.6rem; font-weight: 700; color: #1E293B; margin-bottom: 0.5rem;}
    h2 {font-size: 1.3rem; font-weight: 600; color: #1E293B; margin-top: 1rem; margin-bottom: 0.5rem;}
    h3 {font-size: 1.1rem; font-weight: 600; color: #334155; margin-top: 0.75rem; margin-bottom: 0.3rem;}

    /* --- Dividers --- */
    hr {margin: 1rem 0; border-color: #E2E8F0;}

    /* --- Download buttons --- */
    .stDownloadButton button {
        border-radius: 6px; font-weight: 600;
    }

    /* --- File uploader --- */
    div[data-testid="stFileUploader"] {
        border: 2px dashed #CBD5E1;
        border-radius: 8px;
        padding: 0.5rem;
        background: white;
    }
    div[data-testid="stFileUploader"]:hover {
        border-color: #0D7377;
    }
</style>
"""


def main():
    st.set_page_config(page_title="SPC App", page_icon="📊", layout="wide")
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    if "repo" not in st.session_state:
        st.session_state.repo = SqliteRepository(DB_FILE)

    role, page, param = render_sidebar()

    if role == "Operator" and page == "Data Entry":
        render_data_entry(st.session_state.repo)

    elif role == "Engineer" and page == "SPC Analysis":
        render_spc_analysis(st.session_state.repo, param)

    elif role == "Manager" and page == "Dashboard":
        render_dashboard(st.session_state.repo)


if __name__ == "__main__":
    main()
