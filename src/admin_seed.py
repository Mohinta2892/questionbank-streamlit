from __future__ import annotations

import uuid
import re
import sqlite3
from typing import Optional

from .config import value
from .database import connect, init_db
from .passwords import hash_password
from .seed import utc_now


def emails(name: str) -> list[str]:
    return [email.strip().lower() for email in value(name).split(",") if email.strip()]


def people(names_env: str, emails_env: str) -> list[tuple[str, str]]:
    raw = value(names_env)
    if raw:
        rows = []
        for item in [part.strip() for part in raw.split(",") if part.strip()]:
            match = re.fullmatch(r"(.+?)\s*<([^>]+)>", item)
            email = (match.group(2) if match else item).strip().lower()
            display_name = (match.group(1) if match else email.split("@")[0]).strip()
            rows.append((email, display_name))
        return rows
    return [(email, email.split("@")[0]) for email in emails(emails_env)]


def passwords() -> dict[str, str]:
    rows = {}
    for item in [part.strip() for part in value("USER_PASSWORDS").split(",") if part.strip()]:
        email, sep, password = item.partition("=")
        if sep and password:
            rows[email.strip().lower()] = password
    return rows


def seed_configured_users(conn: Optional[sqlite3.Connection] = None) -> None:
    own_conn = conn is None
    conn = conn or connect()
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

    password_by_email = passwords()
    for role, names_env, emails_env in [
        ("interviewer", "INTERVIEWERS", "INTERVIEWER_EMAILS"),
        ("candidate", "CANDIDATES", "CANDIDATE_EMAILS"),
    ]:
        for email, display_name in people(names_env, emails_env):
            user = conn.execute("SELECT id FROM users WHERE lower(email) = lower(?)", (email,)).fetchone()
            user_id = user["id"] if user else str(uuid.uuid4())
            password_hash = hash_password(password_by_email[email]) if email in password_by_email else None
            if not user:
                conn.execute(
                    "INSERT INTO users (id, email, display_name, role, password_hash, active, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (user_id, email, display_name, role, password_hash, 1, now),
                )
            else:
                conn.execute(
                    "UPDATE users SET display_name = ?, role = ?, password_hash = COALESCE(?, password_hash), active = 1 WHERE id = ?",
                    (display_name, role, password_hash, user_id),
                )
            if role == "candidate":
                existing = conn.execute("SELECT 1 FROM candidate_assessments WHERE user_id = ?", (user_id,)).fetchone()
                if not existing:
                    conn.execute(
                        "INSERT INTO candidate_assessments VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (str(uuid.uuid4()), user_id, assessment_id["id"], "variant-a", "NOT_STARTED", None, None, None),
                    )
    conn.commit()
    if own_conn:
        conn.close()


def main() -> None:
    seed_configured_users()


if __name__ == "__main__":
    main()
