from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / "src").is_dir())))

from src.auth import require_user
from src.services import candidate_assessment_for_user, latest_submission


st.set_page_config(page_title="Result", layout="wide")
conn, user = require_user()

if user["role"] != "candidate":
    st.title("Candidate result")
    st.info("This page is only for candidates. Use the Interviewer page to review candidate activity and submissions.")
    st.stop()

ca = candidate_assessment_for_user(conn, user["id"])
st.title("Submission confirmation")
if not ca:
    st.info("No assessment is assigned to this account.")
else:
    st.write(f"State: **{ca['state']}**")
    latest = latest_submission(conn, ca["id"])
    if latest:
        st.write("Stored SHA-256:")
        st.code(latest["sha256"])
    else:
        st.info("No final ZIP has been uploaded yet.")
conn.close()
