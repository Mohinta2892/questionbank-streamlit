from __future__ import annotations

import json
import sqlite3

from .seed import utc_now


def record(conn: sqlite3.Connection, candidate_assessment_id, event_type: str, **metadata: object) -> None:
    conn.execute(
        "INSERT INTO audit_events (candidate_assessment_id, event_type, event_time, metadata) VALUES (?, ?, ?, ?)",
        (candidate_assessment_id, event_type, utc_now(), json.dumps(metadata, sort_keys=True)),
    )
