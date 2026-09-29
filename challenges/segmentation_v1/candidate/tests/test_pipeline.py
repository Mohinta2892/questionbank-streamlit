import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import load_sample, make_cremi_like_sample, middle_slice
from src.pipeline import segment, write_metadata


def test_starter_pipeline_outputs_mask_and_metadata(tmp_path):
    raw_path = tmp_path / "sample.npy"
    volume, labels = load_sample(raw_path)
    mask = segment(volume, 0.54)

    class Args:
        input = str(raw_path)
        output = str(tmp_path / "mask.npy")
        threshold = 0.54

    metadata = tmp_path / "metadata.json"
    write_metadata(metadata, Args, mask, labels)

    assert raw_path.exists()
    assert (tmp_path / "sample_labels.npy").exists()
    assert mask.shape == volume.shape
    assert mask.dtype == np.uint8
    assert metadata.read_text().count("model_version") == 1


def test_sample_has_2d_slices_and_3d_labels(tmp_path):
    raw, labels = make_cremi_like_sample()
    assert raw.ndim == 3
    assert labels.ndim == 3
    assert middle_slice(raw).ndim == 2
    assert set(np.unique(labels)) >= {0, 1, 2}


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__]))
