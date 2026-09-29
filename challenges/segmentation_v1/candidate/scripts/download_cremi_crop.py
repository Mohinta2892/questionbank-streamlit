from __future__ import annotations

import argparse
import hashlib
import urllib.request
from pathlib import Path

import numpy as np


CREMI = {
    "A": (
        "https://cremi.org/static/data/sample_A_20160501.hdf",
        "4c563d1b78acb2bcfb3ea958b6fe1533422f7f4a19f3e05b600bfa11430b510d",
    ),
    "B": (
        "https://cremi.org/static/data/sample_B_20160501.hdf",
        "887e85521e00deead18c94a21ad71f278d88a5214c7edeed943130a1f4bb48b8",
    ),
    "C": (
        "https://cremi.org/static/data/sample_C_20160501.hdf",
        "2874496f224d222ebc29d0e4753e8c458093e1d37bc53acd1b69b19ed1ae7052",
    ),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Download CREMI and extract a tiny labelled crop.")
    parser.add_argument("--sample", choices=sorted(CREMI), default="A")
    parser.add_argument("--cache-dir", default="data/cremi_cache")
    parser.add_argument("--out", default="data/cremi_sample.hdf")
    parser.add_argument("--z", type=int, default=40)
    parser.add_argument("--y", type=int, default=512)
    parser.add_argument("--x", type=int, default=512)
    parser.add_argument("--depth", type=int, default=32)
    parser.add_argument("--height", type=int, default=128)
    parser.add_argument("--width", type=int, default=128)
    args = parser.parse_args()

    try:
        import h5py
    except ImportError as exc:
        raise SystemExit("Install optional dependency first: python -m pip install h5py") from exc

    url, expected = CREMI[args.sample]
    cache_path = Path(args.cache_dir) / Path(url).name
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    if not cache_path.exists():
        print(f"downloading {url}")
        urllib.request.urlretrieve(url, cache_path)

    actual = sha256(cache_path)
    if actual != expected:
        raise SystemExit(f"checksum mismatch for {cache_path}: expected {expected}, got {actual}")

    crop = np.s_[args.z : args.z + args.depth, args.y : args.y + args.height, args.x : args.x + args.width]
    with h5py.File(cache_path, "r") as h5:
        raw = h5["volumes/raw"][crop]
        labels = h5["volumes/labels/neuron_ids"][crop]

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(args.out, "w") as h5:
        volumes = h5.create_group("volumes")
        label_group = volumes.create_group("labels")
        volumes.create_dataset("raw", data=raw, compression="gzip")
        label_group.create_dataset("neuron_ids", data=labels, compression="gzip")
    print(f"wrote {args.out} shape={raw.shape}")


if __name__ == "__main__":
    main()
