import streamlit as st
from pathlib import Path
from datetime import datetime
from config import DATA_FILE, DATA_DIR


UPLOADS_DIR = DATA_DIR / "uploads"


def render_data_source() -> Path:
    st.subheader("Data Source")
    col1, col2 = st.columns(2)
    with col1:
        use_default = st.checkbox("Use sample data", value=True)
    if use_default:
        return DATA_FILE
    with col2:
        uploaded = st.file_uploader("Upload CSV", type=["csv"])
        if uploaded is not None:
            # Save a timestamped copy as audit trail
            ts = datetime.now().strftime("%Y%m%d-%H%M%S")
            archive_path = UPLOADS_DIR / f"{ts}-{uploaded.name}"
            with open(archive_path, "wb") as f:
                f.write(uploaded.getbuffer())
            return archive_path
    return DATA_FILE
