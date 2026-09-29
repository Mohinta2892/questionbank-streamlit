from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import Optional

from . import storage
from .audit import record
from .config import settings
from .seed import utc_now


def parse_time(value: Optional[str]) -> Optional[datetime]:
    return datetime.fromisoformat(value) if value else None


def refresh_expiry(conn: sqlite3.Connection, ca_id: str) -> None:
    row = conn.execute("SELECT state, expires_at FROM candidate_assessments WHERE id = ?", (ca_id,)).fetchone()
    if row and row["state"] == "IN_PROGRESS" and parse_time(row["expires_at"]) <= datetime.now(timezone.utc):
        conn.execute("UPDATE candidate_assessments SET state = 'EXPIRED' WHERE id = ?", (ca_id,))
        record(conn, ca_id, "assessment_expired")
        conn.commit()


def get_user(conn: sqlite3.Connection, email: str) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM users WHERE lower(email) = lower(?) AND active = 1", (email,)).fetchone()


def list_users(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM users WHERE active = 1 ORDER BY role, email").fetchall()


def candidate_assessment_for_user(conn: sqlite3.Connection, user_id: str) -> Optional[sqlite3.Row]:
    row = conn.execute(
        """
        SELECT ca.*, a.name assessment_name, a.duration_minutes, u.email, u.display_name
        FROM candidate_assessments ca
        JOIN assessments a ON a.id = ca.assessment_id
        JOIN users u ON u.id = ca.user_id
        WHERE ca.user_id = ?
        ORDER BY a.created_at DESC
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()
    if row:
        refresh_expiry(conn, row["id"])
        row = conn.execute(
            """
            SELECT ca.*, a.name assessment_name, a.duration_minutes, u.email, u.display_name
            FROM candidate_assessments ca
            JOIN assessments a ON a.id = ca.assessment_id
            JOIN users u ON u.id = ca.user_id
            WHERE ca.id = ?
            """,
            (row["id"],),
        ).fetchone()
    return row


def start_assessment(conn: sqlite3.Connection, ca_id: str, user_id: str) -> sqlite3.Row:
    conn.execute("BEGIN IMMEDIATE")
    row = conn.execute(
        """
        SELECT ca.*, a.duration_minutes
        FROM candidate_assessments ca
        JOIN assessments a ON a.id = ca.assessment_id
        WHERE ca.id = ? AND ca.user_id = ?
        """,
        (ca_id, user_id),
    ).fetchone()
    if not row:
        raise PermissionError("Assessment not found")
    if row["state"] == "NOT_STARTED":
        started = datetime.now(timezone.utc)
        expires = started + timedelta(minutes=row["duration_minutes"])
        conn.execute(
            "UPDATE candidate_assessments SET state = 'IN_PROGRESS', started_at = ?, expires_at = ? WHERE id = ?",
            (started.isoformat(timespec="seconds"), expires.isoformat(timespec="seconds"), ca_id),
        )
        record(conn, ca_id, "assessment_started")
    conn.commit()
    return conn.execute("SELECT * FROM candidate_assessments WHERE id = ?", (ca_id,)).fetchone()


def assert_writable(conn: sqlite3.Connection, ca_id: str) -> None:
    refresh_expiry(conn, ca_id)
    row = conn.execute("SELECT state FROM candidate_assessments WHERE id = ?", (ca_id,)).fetchone()
    if not row or row["state"] != "IN_PROGRESS":
        raise PermissionError("Assessment is read-only")


def save_response(conn: sqlite3.Connection, ca_id: str, section: str, response: str) -> None:
    assert_writable(conn, ca_id)
    conn.execute(
        """
        INSERT INTO written_responses (candidate_assessment_id, section, response, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(candidate_assessment_id, section)
        DO UPDATE SET response = excluded.response, updated_at = excluded.updated_at
        """,
        (ca_id, section, response, utc_now()),
    )
    record(conn, ca_id, "response_saved", section=section)
    conn.commit()


def responses(conn: sqlite3.Connection, ca_id: str) -> dict[str, str]:
    return {
        row["section"]: row["response"]
        for row in conn.execute("SELECT section, response FROM written_responses WHERE candidate_assessment_id = ?", (ca_id,))
    }


def add_section_seconds(conn: sqlite3.Connection, ca_id: str, section: str, seconds: int) -> None:
    if seconds <= 0:
        return
    conn.execute(
        """
        INSERT INTO section_time (candidate_assessment_id, section, seconds, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(candidate_assessment_id, section)
        DO UPDATE SET seconds = seconds + excluded.seconds, updated_at = excluded.updated_at
        """,
        (ca_id, section, seconds, utc_now()),
    )
    conn.commit()


def section_times(conn: sqlite3.Connection, ca_id: str) -> dict[str, int]:
    return {
        row["section"]: row["seconds"]
        for row in conn.execute("SELECT section, seconds FROM section_time WHERE candidate_assessment_id = ?", (ca_id,))
    }


def reset_candidate_attempt(conn: sqlite3.Connection, user_id: str) -> None:
    row = candidate_assessment_for_user(conn, user_id)
    if not row:
        return
    ca_id = row["id"]
    submission_ids = [r["id"] for r in conn.execute("SELECT id FROM submissions WHERE candidate_assessment_id = ?", (ca_id,))]
    for submission_id in submission_ids:
        conn.execute("DELETE FROM test_runs WHERE submission_id = ?", (submission_id,))
    conn.execute("DELETE FROM submissions WHERE candidate_assessment_id = ?", (ca_id,))
    conn.execute("DELETE FROM written_responses WHERE candidate_assessment_id = ?", (ca_id,))
    conn.execute("DELETE FROM section_time WHERE candidate_assessment_id = ?", (ca_id,))
    conn.execute(
        "UPDATE candidate_assessments SET state = 'NOT_STARTED', started_at = NULL, expires_at = NULL, submitted_at = NULL WHERE id = ?",
        (ca_id,),
    )
    record(conn, ca_id, "dev_attempt_reset")
    conn.commit()


def upload_submission(conn: sqlite3.Connection, ca_id: str, filename: str, data: bytes) -> sqlite3.Row:
    assert_writable(conn, ca_id)
    if not filename.lower().endswith(".zip") or not zipfile.is_zipfile(BytesIO(data)):
        raise ValueError("Upload must be a valid .zip file")
    if len(data) > settings().max_upload_mb * 1024 * 1024:
        raise ValueError("Upload is too large")

    submission_id = str(uuid.uuid4())
    digest = hashlib.sha256(data).hexdigest()
    key = f"submissions/{ca_id}/{submission_id}.zip"
    storage.save_bytes(key, data)
    conn.execute("UPDATE submissions SET is_final = 0 WHERE candidate_assessment_id = ?", (ca_id,))
    conn.execute(
        """
        INSERT INTO submissions
        VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        """,
        (submission_id, ca_id, key, filename.split("/")[-1].split("\\")[-1], digest, len(data), utc_now()),
    )
    record(conn, ca_id, "submission_uploaded", sha256=digest, byte_size=len(data))
    conn.commit()
    return conn.execute("SELECT * FROM submissions WHERE id = ?", (submission_id,)).fetchone()


def submit_assessment(conn: sqlite3.Connection, ca_id: str) -> None:
    assert_writable(conn, ca_id)
    if not latest_submission(conn, ca_id):
        raise ValueError("Upload a final ZIP before submitting")
    conn.execute(
        "UPDATE candidate_assessments SET state = 'SUBMITTED', submitted_at = ? WHERE id = ?",
        (utc_now(), ca_id),
    )
    record(conn, ca_id, "assessment_submitted")
    conn.commit()


def latest_submission(conn: sqlite3.Connection, ca_id: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM submissions WHERE candidate_assessment_id = ? AND is_final = 1 ORDER BY uploaded_at DESC LIMIT 1",
        (ca_id,),
    ).fetchone()


def submissions(conn: sqlite3.Connection, ca_id: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM submissions WHERE candidate_assessment_id = ? ORDER BY is_final DESC, uploaded_at DESC",
        (ca_id,),
    ).fetchall()


def interviewer_rows(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT ca.id, u.email candidate, a.name assessment, ca.variant_id, ca.state,
               ca.started_at, ca.expires_at, ca.submitted_at, s.sha256 latest_sha256,
               tr.state hidden_test_status
        FROM candidate_assessments ca
        JOIN users u ON u.id = ca.user_id
        JOIN assessments a ON a.id = ca.assessment_id
        LEFT JOIN submissions s ON s.candidate_assessment_id = ca.id AND s.is_final = 1
        LEFT JOIN test_runs tr ON tr.submission_id = s.id
        ORDER BY u.email
        """
    ).fetchall()


def queue_test_run(conn: sqlite3.Connection, submission_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT candidate_assessment_id FROM submissions WHERE id = ?", (submission_id,)).fetchone()
    if not row:
        raise ValueError("Submission not found")
    run_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO test_runs (id, submission_id, state, report) VALUES (?, ?, 'QUEUED', ?)",
        (run_id, submission_id, json.dumps({"message": "Runner pickup pending"})),
    )
    record(conn, row["candidate_assessment_id"], "hidden_test_run_started", state="QUEUED")
    conn.commit()
    return conn.execute("SELECT * FROM test_runs WHERE id = ?", (run_id,)).fetchone()
