from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


BASE_DIR = Path(__file__).resolve().parents[1]


def value(name: str, default: str = "") -> str:
    if name in os.environ:
        return os.environ[name]
    try:
        import streamlit as st

        return str(st.secrets.get(name, default))
    except Exception:
        return default


@dataclass(frozen=True)
class Settings:
    app_env: str = value("APP_ENV", "production")
    data_dir: Path = Path(value("DATA_DIR", str(BASE_DIR / "data")))
    db_path: Path = Path(value("DB_PATH", str(BASE_DIR / "data" / "app.sqlite3")))
    storage_backend: str = value("STORAGE_BACKEND", "local")
    storage_dir: Path = Path(value("STORAGE_DIR", str(BASE_DIR / "data" / "objects")))
    s3_bucket: str = value("S3_BUCKET")
    s3_endpoint_url: Optional[str] = value("S3_ENDPOINT_URL") or None
    max_upload_mb: int = int(value("MAX_UPLOAD_MB", "100"))

    @property
    def development_auth(self) -> bool:
        return self.app_env == "development"


def settings() -> Settings:
    return Settings()
