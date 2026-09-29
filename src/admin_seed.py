from __future__ import annotations

import uuid

from .config import value
from .database import connect, init_db
from .seed import utc_now


def emails(name: str) -> list[str]:
    return [email.strip().lower() for email in value(name).split(",") if email.strip()]


def main() -> None:
    conn = connect()
    init_db(conn)
    now = utc_now()
    assessment_id = conn.execute(
        "SELECT id FROM assessments WHERE name = ? AND version = ?",
        ("Segmentation Engineering", "v1"),
    ).fetchone()
    if not assessment_id:
        assessment_id = {"id": str(uuid.uuid4())}
        conn.execute(
            "INSERT INTO assessments VALUES (?, ?, ?, ?, ?, ?)",
            (assessment_id["id"], "Segmentation Engineering", "v1", 90, 1, now),
        )

    for role, env_name in [("interviewer", "INTERVIEWER_EMAILS"), ("candidate", "CANDIDATE_EMAILS")]:
        for email in emails(env_name):
            user = conn.execute("SELECT id FROM users WHERE lower(email) = lower(?)", (email,)).fetchone()
            user_id = user["id"] if user else str(uuid.uuid4())
            if not user:
                conn.execute(
                    "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, email, email.split("@")[0], role, 1, now),
                )
            if role == "candidate":
                existing = conn.execute("SELECT 1 FROM candidate_assessments WHERE user_id = ?", (user_id,)).fetchone()
                if not existing:
                    conn.execute(
                        "INSERT INTO candidate_assessments VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (str(uuid.uuid4()), user_id, assessment_id["id"], "variant-a", "NOT_STARTED", None, None, None),
                    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
