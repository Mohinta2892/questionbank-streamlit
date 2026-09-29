from __future__ import annotations

import json
import zipfile
from io import BytesIO
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHALLENGE = ROOT / "challenges" / "segmentation_v1"


def code_review_fixture() -> str:
    return (CHALLENGE / "code_review_fixture.py").read_text()


def starter_zip(conn, candidate_assessment) -> bytes:
    buf = BytesIO()
    public_root = CHALLENGE / "candidate"
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in public_root.rglob("*"):
            rel = path.relative_to(public_root)
            if path.is_file() and not _excluded(rel):
                zf.write(path, Path("segmentation_v1") / rel)
        zf.writestr(
            "segmentation_v1/config/candidate.json",
            json.dumps(
                {
                    "candidate_assessment_id": candidate_assessment["id"],
                    "variant_id": candidate_assessment["variant_id"],
                },
                indent=2,
            ),
        )
    return buf.getvalue()


def _excluded(path: Path) -> bool:
    parts = set(path.parts)
    return (
        "__pycache__" in parts
        or ".pytest_cache" in parts
        or "outputs" in parts
        or "cremi_cache" in parts
        or path.suffix == ".pyc"
        or path.name in {"sample.npy", "sample_labels.npy"}
    )
