from __future__ import annotations

from pathlib import Path

import numpy as np


def make_cremi_like_sample(shape: tuple[int, int, int] = (48, 64, 64)) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(7)
    z, y, x = np.indices(shape)
    neuron_a = ((z - 18) ** 2 / 15**2 + (y - 24) ** 2 / 14**2 + (x - 26) ** 2 / 14**2) < 1
    neuron_b = ((z - 30) ** 2 / 13**2 + (y - 42) ** 2 / 15**2 + (x - 38) ** 2 / 15**2) < 1

    labels = np.zeros(shape, dtype="uint16")
    labels[neuron_a] = 1
    labels[neuron_b] = 2

    raw = rng.normal(0.25, 0.07, shape).astype("float32")
    raw[labels > 0] += 0.45
    raw += (z / max(1, shape[0] - 1) * 0.08).astype("float32")
    return raw, labels


def load_sample(path: Path) -> tuple[np.ndarray, np.ndarray]:
    if path.suffix in {".h5", ".hdf", ".hdf5"}:
        import h5py

        with h5py.File(path, "r") as h5:
            return h5["volumes/raw"][:], h5["volumes/labels/neuron_ids"][:]

    if path.exists():
        labels = path.with_name(path.stem + "_labels.npy")
        if labels.exists():
            return np.load(path), np.load(labels)

    raw, labels = make_cremi_like_sample()
    path.parent.mkdir(parents=True, exist_ok=True)
    np.save(path, raw)
    np.save(path.with_name(path.stem + "_labels.npy"), labels)
    return raw, labels


def middle_slice(volume: np.ndarray) -> np.ndarray:
    return volume[volume.shape[0] // 2]
