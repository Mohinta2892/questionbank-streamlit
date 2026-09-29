from __future__ import annotations

from pathlib import Path

from .config import settings


def save_bytes(key: str, data: bytes) -> None:
    cfg = settings()
    if cfg.storage_backend == "s3":
        import boto3

        boto3.client("s3", endpoint_url=cfg.s3_endpoint_url).put_object(
            Bucket=cfg.s3_bucket,
            Key=key,
            Body=data,
        )
        return

    path = _local_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as fh:
        fh.write(data)


def read_bytes(key: str) -> bytes:
    cfg = settings()
    if cfg.storage_backend == "s3":
        import boto3

        return boto3.client("s3", endpoint_url=cfg.s3_endpoint_url).get_object(
            Bucket=cfg.s3_bucket,
            Key=key,
        )["Body"].read()
    return _local_path(key).read_bytes()


def _local_path(key: str) -> Path:
    clean = Path(*[part for part in key.split("/") if part and part not in {".", ".."}])
    return settings().storage_dir / clean
