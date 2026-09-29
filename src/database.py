from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from .config import settings


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('candidate', 'interviewer', 'admin')),
    password_hash TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS assessments (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS candidate_assessments (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    assessment_id TEXT NOT NULL REFERENCES assessments(id),
    variant_id TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('NOT_STARTED', 'IN_PROGRESS', 'SUBMITTED', 'EXPIRED')),
    started_at TEXT,
    expires_at TEXT,
    submitted_at TEXT
);

CREATE TABLE IF NOT EXISTS written_responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_assessment_id TEXT NOT NULL REFERENCES candidate_assessments(id),
    section TEXT NOT NULL,
    response TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(candidate_assessment_id, section)
);

CREATE TABLE IF NOT EXISTS section_time (
    candidate_assessment_id TEXT NOT NULL REFERENCES candidate_assessments(id),
    section TEXT NOT NULL,
    seconds INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(candidate_assessment_id, section)
);

CREATE TABLE IF NOT EXISTS submissions (
    id TEXT PRIMARY KEY,
    candidate_assessment_id TEXT NOT NULL REFERENCES candidate_assessments(id),
    object_key TEXT NOT NULL UNIQUE,
    original_filename TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    byte_size INTEGER NOT NULL,
    uploaded_at TEXT NOT NULL,
    is_final INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_assessment_id TEXT REFERENCES candidate_assessments(id),
    event_type TEXT NOT NULL,
    event_time TEXT NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS test_runs (
    id TEXT PRIMARY KEY,
    submission_id TEXT NOT NULL REFERENCES submissions(id),
    state TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    exit_code INTEGER,
    visible_tests_passed INTEGER,
    visible_tests_total INTEGER,
    hidden_tests_passed INTEGER,
    hidden_tests_total INTEGER,
    report TEXT NOT NULL DEFAULT '{}',
    stdout_object_key TEXT,
    stderr_object_key TEXT
);
"""


def connect(db_path: Optional[Path] = None) -> sqlite3.Connection:
    path = db_path or settings().db_path
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)")}
    if "password_hash" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
    conn.commit()
