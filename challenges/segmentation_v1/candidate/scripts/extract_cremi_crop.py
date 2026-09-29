from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract a tiny CREMI HDF5 crop into .npy files.")
    parser.add_argument("cremi_h5")
    parser.add_argument("--out", default="data/cremi_sample.hdf")
    parser.add_argument("--z", type=int, default=0)
    parser.add_argument("--y", type=int, default=0)
    parser.add_argument("--x", type=int, default=0)
    parser.add_argument("--depth", type=int, default=32)
    parser.add_argument("--height", type=int, default=128)
    parser.add_argument("--width", type=int, default=128)
    args = parser.parse_args()

    try:
        import h5py
    except ImportError as exc:
        raise SystemExit("Install optional dependency first: python -m pip install h5py") from exc

    crop = np.s_[args.z : args.z + args.depth, args.y : args.y + args.height, args.x : args.x + args.width]
    with h5py.File(args.cremi_h5, "r") as h5:
        raw = h5["volumes/raw"][crop]
        labels = h5["volumes/labels/neuron_ids"][crop]

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(args.out, "w") as out:
        volumes = out.create_group("volumes")
        label_group = volumes.create_group("labels")
        volumes.create_dataset("raw", data=raw, compression="gzip")
        label_group.create_dataset("neuron_ids", data=labels, compression="gzip")
    print(f"wrote {args.out} shape={raw.shape}")


if __name__ == "__main__":
    main()
