#!/bin/sh
set -eu
"${PYTHON:-python3}" -m src.pipeline \
  --input data/cremi_sample.hdf \
  --output outputs/segmentation.npy \
  --metadata outputs/metadata.json \
  --threshold 0.54
