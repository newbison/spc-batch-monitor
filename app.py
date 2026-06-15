import streamlit as st
from config import DB_FILE
from data_access.sqlite_repository import SqliteRepository
from ui.common.sidebar import render_sidebar
from ui.operator.data_entry import render_data_entry
from ui.engineer.chart_view import render_spc_analysis
from ui.manager.dashboard import render_dashboard
from ui.admin.data_manager import render_data_manager
from ui.engineer.doe_view import render_doe_page

CUSTOM_CSS = """
<style>
    /* Hide Streamlit chrome */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stApp {background: #FAF6F0;}

    /* --- Tighten top padding --- */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
    }

    /* --- Sidebar --- */
    section[data-testid="stSidebar"] {
        background: #3B2A1A;
    }
    section[data-testid="stSidebar"] > div:first-child {padding-top: 0;}
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stCaption {
        color: #D4C4B0 !important;
    }
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stRadio label {
        font-size: 1.1rem; color: #FFFFFF !important; font-weight: 700;
    }
    section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {
        font-size: 1.15rem; color: #FFFFFF !important; font-weight: 700;
    }
    section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:hover {
        color: #F0E6D8 !important;
    }
    section[data-testid="stSidebar"] .sidebar-header {
        background: linear-gradient(180deg, #4A3520, #3B2A1A);
        padding: 1.2rem 1rem 0.8rem 1rem;
        margin: 0 -1rem 1rem -1rem;
        color: #F0E6D8;
        border-bottom: 2px solid #C4734F;
    }
    section[data-testid="stSidebar"] .sidebar-header h1 {
        color: #F0E6D8; font-size: 1.3rem; margin: 0; font-weight: 700;
    }
    section[data-testid="stSidebar"] .sidebar-header p {
        color: #C4A88C; font-size: 0.8rem; margin: 0.2rem 0 0 0;
    }

    /* --- Metric cards --- */
    div[data-testid="stMetric"] {
        background: white;
        border: 1px solid #E0D3C0;
        border-radius: 6px;
        padding: 1rem 1.2rem;
        box-shadow: 0 2px 8px rgba(60,30,10,0.06);
    }
    div[data-testid="stMetric"] > div:first-child {gap: 0;}
    div[data-testid="stMetricLabel"] {
        font-size: 0.72rem; color: #8C735B; font-weight: 600;
        text-transform: uppercase; letter-spacing: 0.05em;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.6rem; font-weight: 700; color: #2C1E0F;
    }

    /* --- Buttons --- */
    button[kind="primary"] {
        border-radius: 4px; font-weight: 600;
        background: #C4734F; border-color: #C4734F;
        transition: all 0.15s ease;
    }
    button[kind="primary"]:hover {
        background: #B56240; border-color: #B56240;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(196,115,79,0.35);
    }

    /* --- Expanders --- */
    div[data-testid="stExpander"] {
        border: 1px solid #E0D3C0;
        border-radius: 6px;
        background: white;
        box-shadow: 0 2px 8px rgba(60,30,10,0.04);
    }
    div[data-testid="stExpander"] > details > summary > span {
        font-weight: 600; font-size: 0.9rem; color: #5C3D2A;
    }

    /* --- DataFrames --- */
    div[data-testid="stDataFrame"] {
        border: 1px solid #E0D3C0;
        border-radius: 6px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(60,30,10,0.04);
    }
    div[data-testid="stDataFrame"] th {
        background: #F5EDE3 !important; color: #5C3D2A !important;
        font-weight: 600; font-size: 0.8rem;
    }

    /* --- Alerts --- */
    .stAlert {
        border-radius: 4px; border-left-width: 4px;
        font-size: 0.88rem; font-weight: 500;
    }
    div[data-testid="stAlert"] [data-testid="stNotificationContentError"] {
        border-left-color: #C4523E;
    }

    /* --- Typography --- */
    h1 {font-size: 1.6rem; font-weight: 700; color: #2C1E0F; margin-bottom: 0.5rem;}
    h2 {font-size: 1.25rem; font-weight: 600; color: #3B2A1A; margin-top: 1.2rem; margin-bottom: 0.6rem;}
    h3 {font-size: 1.05rem; font-weight: 600; color: #5C3D2A; margin-top: 0.8rem; margin-bottom: 0.4rem;}

    /* --- Dividers --- */
    hr {margin: 1.2rem 0; border-color: #E0D3C0;}

    /* --- Download buttons --- */
    .stDownloadButton button {
        border-radius: 4px; font-weight: 600;
        border: 1px solid #C4734F; color: #C4734F;
        background: transparent;
    }
    .stDownloadButton button:hover {
        background: #C4734F; color: white;
    }

    /* --- File uploader --- */
    div[data-testid="stFileUploader"] {
        border: 2px dashed #D4C4B0;
        border-radius: 6px;
        padding: 1rem;
        background: white;
    }
    div[data-testid="stFileUploader"]:hover {
        border-color: #C4734F;
    }

    /* --- Tabs --- */
    button[data-testid="stBaseButton-secondary"] {
        color: #5C3D2A;
    }
    button[data-testid="stBaseButton-secondary"][aria-selected="true"] {
        color: #C4734F;
        border-bottom-color: #C4734F;
    }

    /* --- Select boxes --- */
    .stSelectbox div[data-baseweb="select"] > div {
        background: white;
        border: 1px solid #E0D3C0;
        border-radius: 4px;
    }
    .stSelectbox div[data-baseweb="select"] > div:hover {
        border-color: #C4734F;
    }
</style>
"""


def main():
    st.set_page_config(page_title="SPC App", page_icon="📊", layout="wide")
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    if "repo" not in st.session_state:
        st.session_state.repo = SqliteRepository(DB_FILE)

    role, page, param = render_sidebar(st.session_state.repo)

    if page == "DOE":
        render_doe_page(st.session_state.repo)

    elif role == "Operator" and page == "Data Entry":
        render_data_entry(st.session_state.repo)

    elif role == "Engineer" and page == "SPC Analysis":
        render_spc_analysis(st.session_state.repo, param)

    elif role == "Manager" and page == "Dashboard":
        render_dashboard(st.session_state.repo)

    elif role == "Admin" and page == "Data Management":
        render_data_manager(st.session_state.repo)


if __name__ == "__main__":
    main()
