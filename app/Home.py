from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / "src").is_dir())))

from src.auth import require_user
from src.config import settings


st.set_page_config(page_title="Assessment Platform", page_icon=":material/assignment:", layout="wide")

conn, user = require_user()

st.title("Technical Assessment")
st.write(f"Signed in as **{user['display_name']}** ({user['role']}).")

if settings().development_auth:
    st.info("Development auth is enabled because APP_ENV=development.")

if user["role"] == "candidate":
    st.page_link("pages/01_Assessment.py", label="Open assessment", icon=":material/assignment:")
    st.page_link("pages/02_Submit.py", label="Submit final ZIP", icon=":material/upload_file:")
else:
    st.page_link("pages/90_Interviewer.py", label="Interviewer dashboard", icon=":material/dashboard:")

conn.close()
