from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / "src").is_dir())))

from src.auth import require_user
from src.services import candidate_assessment_for_user, latest_submission, submit_assessment, upload_submission


st.set_page_config(page_title="Submit", layout="wide")
conn, user = require_user()

if user["role"] != "candidate":
    st.stop()

ca = candidate_assessment_for_user(conn, user["id"])
if not ca:
    st.error("No assessment assigned.")
    st.stop()

st.title("Final submission")
st.caption(f"State: {ca['state']}")
readonly = ca["state"] != "IN_PROGRESS"

uploaded = st.file_uploader("Upload final ZIP", type=["zip"], disabled=readonly)
if uploaded and st.button("Store ZIP", disabled=readonly):
    try:
        sub = upload_submission(conn, ca["id"], uploaded.name, uploaded.getvalue())
        st.success("Stored submission")
        st.code(sub["sha256"])
    except (PermissionError, ValueError) as exc:
        st.error(str(exc))

latest = latest_submission(conn, ca["id"])
if latest:
    st.write("Current final submission")
    st.code(latest["sha256"])
    st.write(f"{latest['original_filename']} ({latest['byte_size']} bytes)")

confirm = st.checkbox("I confirm this is my final submission.", disabled=readonly or not latest)
if st.button("Submit assessment", disabled=readonly or not confirm or not latest):
    try:
        submit_assessment(conn, ca["id"])
        st.success("Assessment submitted. Thank you.")
        st.rerun()
    except (PermissionError, ValueError) as exc:
        st.error(str(exc))

conn.close()
