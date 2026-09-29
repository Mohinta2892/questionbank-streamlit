from __future__ import annotations

import uuid
from datetime import datetime, timezone

from .database import connect, init_db


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def seed() -> None:
    conn = connect()
    init_db(conn)
    if conn.execute("SELECT 1 FROM users LIMIT 1").fetchone():
        conn.execute(
            "UPDATE assessments SET duration_minutes = 90 WHERE name = ? AND version = ?",
            ("Segmentation Engineering", "v1"),
        )
        conn.commit()
        conn.close()
        return

    now = utc_now()
    interviewer_id = str(uuid.uuid4())
    candidate_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
    assessment_id = str(uuid.uuid4())

    conn.executemany(
        "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)",
        [
            (interviewer_id, "interviewer@example.com", "Ivy Interviewer", "interviewer", 1, now),
            (candidate_ids[0], "candidate1@example.com", "Casey Candidate", "candidate", 1, now),
            (candidate_ids[1], "candidate2@example.com", "Riley Candidate", "candidate", 1, now),
        ],
    )
    conn.execute(
        "INSERT INTO assessments VALUES (?, ?, ?, ?, ?, ?)",
        (assessment_id, "Segmentation Engineering", "v1", 90, 1, now),
    )
    conn.executemany(
        "INSERT INTO candidate_assessments VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (str(uuid.uuid4()), candidate_ids[0], assessment_id, "variant-a", "NOT_STARTED", None, None, None),
            (str(uuid.uuid4()), candidate_ids[1], assessment_id, "variant-b", "NOT_STARTED", None, None, None),
        ],
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    seed()
