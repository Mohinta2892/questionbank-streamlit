from __future__ import annotations

import sys
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import streamlit as st

sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / "src").is_dir())))

from src.auth import require_user
from src import storage
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
    if ca["state"] == "SUBMITTED":
        record_key = latest["object_key"].rsplit(".", 1)[0] + ".json"
        archive = BytesIO()
        with ZipFile(archive, "w", ZIP_DEFLATED) as bundle:
            bundle.writestr(f"submission/{latest['original_filename']}", storage.read_bytes(latest["object_key"]))
            bundle.writestr("assessment_record.json", storage.read_bytes(record_key))
        st.download_button(
            "Download submission and assessment record",
            data=archive.getvalue(),
            file_name=f"{ca['id']}_submission_archive.zip",
            mime="application/zip",
        )

confirm = st.checkbox("I confirm this is my final submission.", disabled=readonly or not latest)
if st.button("Submit assessment", disabled=readonly or not confirm or not latest):
    try:
        submit_assessment(conn, ca["id"])
        st.success("Assessment submitted. The assessment record is saved beside the ZIP and is available to download below.")
        st.rerun()
    except (PermissionError, ValueError) as exc:
        st.error(str(exc))

conn.close()
