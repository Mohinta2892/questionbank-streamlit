from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from src.data import load_sample


MODEL_NAME = "toy-threshold-segmenter"
MODEL_VERSION = "research-2026-09"
DATASET_NAME = "cremi-style-tiny-fixture"


def segment(volume: np.ndarray, threshold: float) -> np.ndarray:
    smoothed = (
        volume
        + np.roll(volume, 1, axis=0)
        + np.roll(volume, -1, axis=0)
        + np.roll(volume, 1, axis=1)
        + np.roll(volume, -1, axis=1)
    ) / 5
    return (smoothed > threshold).astype("uint8")


def dice_score(prediction: np.ndarray, labels: np.ndarray) -> float:
    target = labels > 0
    pred = prediction > 0
    denom = pred.sum() + target.sum()
    return float(2 * np.logical_and(pred, target).sum() / denom) if denom else 1.0


def write_metadata(path: Path, args: argparse.Namespace, output: np.ndarray, labels: np.ndarray) -> None:
    # TODO: Record tile shape, overlap, input path, output path, model version,
    # threshold, output shape/dtype, and evaluation values.
    metadata = {
        "dataset_name": DATASET_NAME,
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "input": args.input,
        "output": args.output,
        "threshold": args.threshold,
        "output_shape": list(output.shape),
        "output_dtype": str(output.dtype),
        "foreground_dice": round(dice_score(output, labels), 4),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metadata, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--metadata", required=True)
    parser.add_argument("--threshold", type=float, default=0.5)
    args = parser.parse_args()

    volume, labels = load_sample(Path(args.input))
    # TODO: Replace this whole-volume inference with tiled inference using
    # src.tiling.plan_tiles. Keep output.shape == volume.shape.
    output = segment(volume, args.threshold)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(output_path, output)
    # TODO: Save or document representative 2-D slices for inspection.
    write_metadata(Path(args.metadata), args, output, labels)
    print(f"wrote {output_path} shape={output.shape} dice={dice_score(output, labels):.3f}")


if __name__ == "__main__":
    main()
