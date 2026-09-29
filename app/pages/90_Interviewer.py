from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / "src").is_dir())))

from src import storage
from src.auth import require_interviewer, require_user
from src.services import interviewer_rows, latest_submission, queue_test_run, reset_assessment_timer, responses, section_times, submissions


st.set_page_config(page_title="Interviewer", layout="wide")
conn, user = require_user()
require_interviewer(user)

st.title("Interviewer dashboard")
rows = interviewer_rows(conn)
st.dataframe([dict(r) for r in rows], hide_index=True, width="stretch")

ids = [r["id"] for r in rows]
selected = st.selectbox("Candidate assessment", ids, format_func=lambda x: next(r["candidate"] for r in rows if r["id"] == x)) if ids else None

if selected:
    selected_row = next(row for row in rows if row["id"] == selected)
    with st.expander("Reset assessment timer"):
        can_reset = selected_row["state"] in {"IN_PROGRESS", "EXPIRED"}
        if can_reset:
            st.warning("This starts a fresh full-duration timer. Saved answers, section times, and uploaded ZIPs are kept.")
            reason = st.text_input("Reason for reset", key=f"timer_reset_reason_{selected}")
            confirmed = st.checkbox("Confirm timer reset", key=f"timer_reset_confirm_{selected}")
            if st.button("Restart timer", disabled=not reason.strip() or not confirmed):
                try:
                    reset_assessment_timer(conn, selected, reason)
                    st.success("Timer restarted.")
                    st.session_state.pop(f"timer_reset_confirm_{selected}", None)
                    st.rerun()
                except (PermissionError, ValueError) as exc:
                    st.error(str(exc))
        else:
            st.info("Timer reset is available only for in-progress or expired assessments. Submitted assessments remain locked.")

    st.subheader("Assessment responses")
    times = section_times(conn, selected)
    if times:
        st.write("Time allocation")
        st.dataframe(
            [{"section": section, "minutes": round(seconds / 60, 1)} for section, seconds in times.items()],
            hide_index=True,
            width="stretch",
        )

    for section, text in responses(conn, selected).items():
        st.markdown(f"**{section}**")
        st.write(text or "_No response_")

    st.subheader("Submission")
    latest = latest_submission(conn, selected)
    if latest:
        st.code(latest["sha256"])
        st.download_button(
            "Download original ZIP",
            data=storage.read_bytes(latest["object_key"]),
            file_name=latest["original_filename"],
            mime="application/zip",
        )
        selected_state = next(row["state"] for row in rows if row["id"] == selected)
        if selected_state == "SUBMITTED":
            record_key = latest["object_key"].rsplit(".", 1)[0] + ".json"
            st.download_button(
                "Download assessment record",
                data=storage.read_bytes(record_key),
                file_name=f"{selected}_assessment_record.json",
                mime="application/json",
            )
        if st.button("Queue hidden tests"):
            run = queue_test_run(conn, latest["id"])
            st.info(f"Recorded as {run['state']}; no test runner is configured yet ({run['id']}).")
    else:
        st.info("No submission yet.")

    with st.expander("Revision history"):
        revisions = submissions(conn, selected)
        st.dataframe([dict(s) for s in revisions], hide_index=True, width="stretch")
        if revisions:
            revision_id = st.selectbox(
                "Download revision",
                [row["id"] for row in revisions],
                format_func=lambda value: next(
                    f"{row['original_filename']} · {row['uploaded_at']}" for row in revisions if row["id"] == value
                ),
            )
            revision = next(row for row in revisions if row["id"] == revision_id)
            st.download_button(
                "Download selected revision",
                data=storage.read_bytes(revision["object_key"]),
                file_name=revision["original_filename"],
                mime="application/zip",
                key=f"download_revision_{revision_id}",
            )

    st.subheader("Interview briefing")
    if latest:
        st.write("- Review decisions against the submitted repository.")
        st.write("- Hidden test runner is queued separately; Streamlit does not execute candidate code.")
    else:
        st.write("- No final artifact to review yet.")

conn.close()
