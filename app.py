"""Hub shell — routes between sub-apps (SPC, DOE, future apps).

Architecture:
    app.py (this file) = Hub: page config, CSS, repo init, app selector
    Each sub-app owns its sidebar section + main content.

Adding a new sub-app:
    1. Write a render function: def _render_xxx(repo): ...
    2. Add an entry to the APPS list below.
    That's it — the sidebar button and routing appear automatically.
"""

import streamlit as st
from config import DB_FILE
from data_access.sqlite_repository import SqliteRepository
from data_access.base import DataRepository

# --- Sub-app renderers (lazy imports inside functions to keep startup fast) ---
from ui.common.sidebar import render_spc_sidebar
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
    /* Force all sidebar text white & large */
    section[data-testid="stSidebar"],
    section[data-testid="stSidebar"] * {
        color: #FFFFFF !important;
    }
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stRadio label,
    section[data-testid="stSidebar"] .stRadio p,
    section[data-testid="stSidebar"] .stRadio span,
    section[data-testid="stSidebar"] [data-baseweb="radio"] label,
    section[data-testid="stSidebar"] [data-baseweb="radio"] span,
    section[data-testid="stSidebar"] [data-baseweb="radio"] p {
        font-size: 1.15rem !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }
    /* Sidebar captions keep muted tone */
    section[data-testid="stSidebar"] .stCaption {
        color: #D4C4B0 !important;
        font-size: 0.8rem !important;
    }

    /* --- Sidebar header --- */
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

    /* --- Sidebar section labels --- */
    .sidebar-section-label {
        color: #C4734F !important;
        font-size: 0.6rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.12em !important;
        text-transform: uppercase;
        margin: 1rem 0 0.3rem 0 !important;
        padding: 0;
    }

    /* --- Sidebar input widgets: dark bg, white text, visible borders --- */
    section[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div {
        background: #4A3520 !important;
        border-color: #6B5A48 !important;
    }
    section[data-testid="stSidebar"] div[data-baseweb="input"] input,
    section[data-testid="stSidebar"] div[data-baseweb="input"] textarea,
    section[data-testid="stSidebar"] input[type="text"],
    section[data-testid="stSidebar"] .stTextInput input,
    section[data-testid="stSidebar"] .stNumberInput input {
        background: #4A3520 !important;
        border-color: #6B5A48 !important;
        color: #FFFFFF !important;
    }
    /* Sidebar dropdown menu (renders in portal — outside sidebar DOM) */
    div[data-baseweb="popover"] ul[role="listbox"] li {
        color: #2C1E0F !important;
        background: #FFFFFF !important;
    }
    div[data-baseweb="popover"] ul[role="listbox"] li:hover {
        background: #F5EDE3 !important;
    }
    /* Selected/highlighted option in dropdown */
    div[data-baseweb="popover"] ul[role="listbox"] li[aria-selected="true"] {
        background: #E8D5C0 !important;
        font-weight: 600;
    }

    /* --- App selector buttons — BIG and prominent --- */
    section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] button {
        font-size: 1.15rem !important;
        font-weight: 800 !important;
        padding: 0.8rem 0.3rem !important;
        min-height: 64px !important;
        border-radius: 10px !important;
        border-width: 2px !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] button[kind="primary"] {
        background: #C4734F !important;
        border-color: #C4734F !important;
        color: #FFFFFF !important;
        box-shadow: 0 4px 12px rgba(196, 115, 79, 0.4);
    }
    section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] button[kind="primary"]:hover {
        background: #D4835F !important;
        border-color: #D4835F !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] button[kind="secondary"] {
        background: rgba(255, 255, 255, 0.08) !important;
        border: 2px solid #6B5A48 !important;
        color: #D4C4B0 !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] button[kind="secondary"]:hover {
        background: rgba(255, 255, 255, 0.15) !important;
        border-color: #C4734F !important;
        color: #FFFFFF !important;
    }

    /* --- Other sidebar buttons (non-selector) --- */
    section[data-testid="stSidebar"] button {
        color: #F0E6D8 !important;
    }
    section[data-testid="stSidebar"] button[kind="primary"] {
        background: #C4734F !important;
        border-color: #C4734F !important;
        font-weight: 600;
        border-radius: 4px;
        color: #FFFFFF !important;
    }
    section[data-testid="stSidebar"] button[kind="secondary"] {
        color: #D4C4B0 !important;
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
        font-size: 0.72rem; color: #4A3728; font-weight: 600;
        text-transform: uppercase; letter-spacing: 0.05em;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.6rem; font-weight: 700; color: #2C1E0F;
    }

    /* --- Main area buttons --- */
    button[kind="primary"] {
        border-radius: 4px; font-weight: 600;
        background: #C4734F; border-color: #C4734F;
        color: #FFFFFF !important;
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
        border: 1px solid #B56240; color: #B56240;
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
    .stTabs [role="tab"] {
        font-size: 0.95rem;
        font-weight: 600;
        padding: 0.6rem 1.4rem;
        color: #4A3728;
    }
    .stTabs [role="tab"][aria-selected="true"] {
        color: #C4734F;
        border-bottom: 3px solid #C4734F;
        background: linear-gradient(0deg, rgba(196,115,79,0.08), transparent);
    }

    /* --- Top role bar --- */
    .role-bar-wrapper button {
        font-size: 1.05rem !important;
        font-weight: 700 !important;
        padding: 0.7rem 0.3rem !important;
        min-height: 52px !important;
        border-radius: 8px !important;
        border-width: 2px !important;
    }
    .role-bar-wrapper button[kind="primary"] {
        background: #C4734F !important;
        border-color: #C4734F !important;
        color: #FFFFFF !important;
        box-shadow: 0 2px 8px rgba(196, 115, 79, 0.3);
    }
    .role-bar-wrapper button[kind="secondary"] {
        background: white !important;
        border: 2px solid #E0D3C0 !important;
        color: #4A3728 !important;
    }
    .role-bar-wrapper button[kind="secondary"]:hover {
        border-color: #C4734F !important;
        color: #C4734F !important;
        background: #FAF6F0 !important;
    }

    /* --- Select boxes --- */
    .stSelectbox div[data-baseweb="select"] > div {
        background: white;
        border: 1px solid #E0D3C0;
        border-radius: 4px;
        color: #2C1E0F !important;
    }
    .stSelectbox div[data-baseweb="select"] > div:hover {
        border-color: #C4734F;
    }

    /* --- Input fields on light backgrounds --- */
    div[data-baseweb="input"] input,
    div[data-baseweb="input"] textarea {
        color: #2C1E0F !important;
    }
</style>
"""


# ---------------------------------------------------------------------------
# Sub-app renderers
# ---------------------------------------------------------------------------

ROLES = ["Operator", "Engineer", "Manager", "Admin"]

PAGE_MAP = {
    "Operator": "Data Entry",
    "Engineer": "SPC Analysis",
    "Manager": "Dashboard",
    "Admin": "Data Management",
}


def _render_role_bar() -> str:
    """Render the role selector as a horizontal button bar at the top of main content."""
    if "role_selector" not in st.session_state:
        st.session_state.role_selector = "Operator"

    st.markdown('<div class="role-bar-wrapper">', unsafe_allow_html=True)
    cols = st.columns(len(ROLES), gap="small")
    for i, role in enumerate(ROLES):
        with cols[i]:
            if st.button(
                role,
                use_container_width=True,
                key=f"role_btn_{role}",
                type="primary" if st.session_state.role_selector == role else "secondary",
            ):
                st.session_state.role_selector = role
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    return st.session_state.role_selector



def _render_spc(repo: DataRepository):
    """SPC sub-app: top role bar + sidebar (engineer ctx) + page routing."""
    role = _render_role_bar()
    page = PAGE_MAP.get(role, "Data Entry")
    param = render_spc_sidebar(repo, role, page)

    if role == "Operator" and page == "Data Entry":
        render_data_entry(repo)
    elif role == "Engineer" and page == "SPC Analysis":
        render_spc_analysis(repo, param)
    elif role == "Manager" and page == "Dashboard":
        render_dashboard(repo)
    elif role == "Admin" and page == "Data Management":
        render_data_manager(repo)


def _render_doe(repo: DataRepository):
    """DOE sub-app: own sidebar + wizard main content."""
    render_doe_page(repo)


# ---------------------------------------------------------------------------
# App registry — add new apps here
# ---------------------------------------------------------------------------

APPS = [
    {
        "key": "SPC",
        "icon": "📊",
        "title": "SPC",
        "subtitle": "Statistical Process Control",
        "render": _render_spc,
    },
    {
        "key": "DOE",
        "icon": "🧪",
        "title": "DOE",
        "subtitle": "Design of Experiments",
        "render": _render_doe,
    },
    # External links (open in new tab, not rendered as sub-app)
]

EXTERNAL_LINKS = [
    {
        "icon": "🧬",
        "title": "Polymer Simulation",
        "url": "https://newbison.github.io/polymer_simulation/",
    },
]


# ---------------------------------------------------------------------------
# Hub main
# ---------------------------------------------------------------------------

def main():
    st.set_page_config(page_title="Forge AI", page_icon="🔥", layout="wide")
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    if "repo" not in st.session_state:
        st.session_state.repo = SqliteRepository(DB_FILE)
    if "current_app" not in st.session_state:
        st.session_state.current_app = "SPC"

    repo = st.session_state.repo
    current = st.session_state.current_app

    # --- Hub sidebar: brand header + app selector ---
    with st.sidebar:
        st.markdown(f"""
        <div class="sidebar-header">
            <h1>🔥  Forge AI</h1>
            <p>AI-Powered Materials Intelligence</p>
        </div>
        """, unsafe_allow_html=True)

        # App selector — big buttons
        st.markdown(
            '<p class="sidebar-section-label">MODULES</p>',
            unsafe_allow_html=True,
        )
        cols = st.columns(len(APPS))
        for i, app in enumerate(APPS):
            with cols[i]:
                is_active = current == app["key"]
                if st.button(
                    f"{app['icon']}  {app['title']}",
                    use_container_width=True,
                    type="primary" if is_active else "secondary",
                    key=f"app_btn_{app['key']}",
                ):
                    st.session_state.current_app = app["key"]
                    st.rerun()

        # External links
        if EXTERNAL_LINKS:
            st.divider()
            st.markdown(
                '<p class="sidebar-section-label">EXTERNAL TOOLS</p>',
                unsafe_allow_html=True,
            )
            for link in EXTERNAL_LINKS:
                st.html(
                    f'<a href="{link["url"]}" target="_blank" rel="noopener noreferrer" '
                    f'style="display:block; text-align:center; '
                    f'font-size:1.15rem; font-weight:800; '
                    f'padding:0.8rem 0.3rem; min-height:64px; '
                    f'line-height:64px; text-decoration:none; '
                    f'border-radius:10px; border:2px solid #6B5A48; '
                    f'background:rgba(255,255,255,0.08); color:#D4C4B0; '
                    f'transition:all 0.15s ease; cursor:pointer;" '
                    f'onclick="window.open(\'{link["url"]}\',\'_blank\',\'noopener,noreferrer\');return false;">'
                    f'{link["icon"]}  {link["title"]}  ↗'
                    f'</a>'
                )

        st.divider()

    # --- Delegate to selected sub-app ---
    for app in APPS:
        if app["key"] == current:
            app["render"](repo)
            break


if __name__ == "__main__":
    main()
