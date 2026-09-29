from __future__ import annotations

from datetime import datetime, timezone
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / "src").is_dir())))

from src.auth import require_user
from src.audit import record
from src.challenge import code_review_fixture, starter_zip
from src.database import connect
from src.services import add_section_seconds, candidate_assessment_for_user, responses, save_response, start_assessment


st.set_page_config(page_title="Assessment", layout="wide")
conn, user = require_user()

if user["role"] != "candidate":
    st.info("Use the interviewer dashboard for candidate results.")
    st.stop()

ca = candidate_assessment_for_user(conn, user["id"])
if not ca:
    st.error("No active assessment is assigned to this account.")
    st.stop()

st.title(ca["assessment_name"])

if ca["state"] == "NOT_STARTED":
    st.subheader("Before you start")
    st.write(f"Duration: **{ca['duration_minutes']} minutes**")
    st.write("Sections:")
    st.write("- Section A: review a short inference snippet and write up what you would prioritise.")
    st.write("- Section B: implement one function in the starter repository. Open `src/tiling.py` and use `tests/test_tiling.py` to guide your work.")
    st.write("- Section C: use tiled inference in the starter pipeline, add checks/evaluation, and document what you changed.")
    st.write("Allowed resources: documentation and your usual editor. Do not share the challenge.")
    st.write("Submit a ZIP containing your final repository and written decisions.")
    ready = st.checkbox("I understand the timer starts when I click Start assessment.")
    if st.button("Start assessment", disabled=not ready):
        start_assessment(conn, ca["id"], user["id"])
        st.rerun()
    st.stop()

sections = {
    "Section A": "Code Review",
    "Section B": "Algorithm",
    "Section C": "Production Challenge",
}
state_prefix = f"section_timer_{ca['id']}"
now = datetime.now(timezone.utc)
previous_section = st.session_state.get(f"{state_prefix}_section")
previous_seen = st.session_state.get(f"{state_prefix}_seen")
if previous_section and previous_seen:
    elapsed = int((now - previous_seen).total_seconds())
    # ponytail: session-based timing misses abandoned tabs; add browser heartbeat if used for scoring.
    add_section_seconds(conn, ca["id"], previous_section, min(elapsed, 600))

section = st.radio("Section", list(sections), horizontal=True, format_func=lambda key: f"{key}: {sections[key]}")
st.session_state[f"{state_prefix}_section"] = section
st.session_state[f"{state_prefix}_seen"] = now

remaining = ""
if ca["expires_at"]:
    seconds = max(0, int((datetime.fromisoformat(ca["expires_at"]) - datetime.now(timezone.utc)).total_seconds()))
    remaining = f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"

st.caption(f"{user['display_name']} | {ca['assessment_name']} | State: {ca['state']} | Remaining: {remaining}")
readonly = ca["state"] != "IN_PROGRESS"
saved = responses(conn, ca["id"])


def audit_starter_download() -> None:
    audit_conn = connect()
    try:
        record(audit_conn, ca["id"], "starter_bundle_downloaded")
        audit_conn.commit()
    finally:
        audit_conn.close()

if section == "Section A":
    st.subheader("Code Review")
    st.write("Explain what this code is doing. Identify the three issues you would prioritise before running it across a 20 TB dataset. Choose one issue and describe or implement how you would fix it.")
    st.code(code_review_fixture(), language="python")
    explanation = st.text_area("Explanation", saved.get("section_a_explanation", ""), disabled=readonly, height=160)
    fix = st.text_area("Prioritised fix", saved.get("section_a_fix", ""), disabled=readonly, height=160)
    if st.button("Save Section A", disabled=readonly):
        save_response(conn, ca["id"], "section_a_explanation", explanation)
        save_response(conn, ca["id"], "section_a_fix", fix)
        st.success("Saved")

if section == "Section B":
    st.subheader("Algorithm")
    st.write("In the downloaded starter repository, implement `plan_tiles(shape, max_tile_shape, overlap)` in `src/tiling.py`. Paste your final implementation below and explain how it handles boundaries, overlap, invalid inputs, and your design tradeoffs.")
    st.write("Use `tests/test_tiling.py` and run `python -m pytest tests/test_tiling.py` from the starter repository to check your work.")
    notes = st.text_area("Implementation and reasoning", saved.get("section_b_notes", ""), disabled=readonly, height=360)
    if st.button("Save Section B", disabled=readonly):
        save_response(conn, ca["id"], "section_b_notes", notes)
        st.success("Saved")

if section == "Section C":
    st.subheader("Production Challenge")
    st.write("Modify the supplied 3-D segmentation pipeline. Implement `plan_tiles` in `src/tiling.py`, then use that tiling logic in `src/pipeline.py` so inference runs on bounded-size 3-D chunks.")
    st.write("Your final repository should still run with `./run_job.sh`, include tests or checks for the behavior you changed, write evaluation metadata, save or document representative output slices, and record commands, failures, fixes, and tradeoffs in `DECISIONS.md`.")
    st.download_button(
        "Download starter repository",
        data=starter_zip(conn, ca),
        file_name=f"segmentation_v1_{ca['variant_id']}.zip",
        mime="application/zip",
        disabled=readonly,
        on_click=audit_starter_download,
    )
    decisions = st.text_area("Engineering decisions", saved.get("decisions", ""), disabled=readonly, height=220)
    if st.button("Save decisions", disabled=readonly):
        save_response(conn, ca["id"], "decisions", decisions)
        st.success("Saved")

conn.close()
