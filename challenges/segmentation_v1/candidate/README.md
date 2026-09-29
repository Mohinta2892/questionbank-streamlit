# Segmentation Pipeline Engineering Challenge

You are inheriting a small research segmentation pipeline for electron microscopy data. The supplied model is intentionally simple and already produces non-empty masks on the provided input. This assessment is about making the inference code runnable, testable, and inspectable.

You have 90 minutes. Leave the repository runnable and use `DECISIONS.md` to explain what you changed, what failed, and what you would do next.

## Goal

Make the current project runnable on the provided CREMI crop and easier for another researcher to check.

Your final submission should include:

1. `./run_job.sh` should produce a segmentation output.
2. A working implementation of `plan_tiles` in `src/tiling.py`.
3. Pipeline changes that use tiling or another bounded-chunk approach for inference.
4. Tests or checks for the behavior you changed.
5. A lightweight evaluation and a way to inspect representative output slices.
6. Short notes in `DECISIONS.md` explaining what you changed, what failed, how you fixed it, what you left alone, and why.

## What we care about

- Sensible pipeline structure.
- Correct behavior on awkward data shapes.
- Practical reliability and reproducibility improvements.
- Tests and evaluation output.
- Clear notes on how this would run on larger volumes.
- Clear communication in `DECISIONS.md`.

We do not expect excellent segmentation metrics, training code, a new model, cloud infrastructure, or a perfect production system.

## Starting point

Run:

```bash
python -m pip install -r requirements.txt
./run_job.sh
python -m pytest tests
```

The pipeline run should succeed immediately. Use the test output to decide what to improve.

## Suggested workflow

1. Implement `plan_tiles(shape, max_tile_shape, overlap)` in `src/tiling.py`. Run `tests/test_tiling.py`.
2. Use that tiling logic in `src/pipeline.py` so inference can run on bounded-size 3-D chunks.
3. Keep `./run_job.sh` as the main entry point and make sure it writes outputs under `outputs/`.
4. Run `tests/test_pipeline.py` before and after pipeline changes. Add or update a small number of tests for the behavior you changed.
5. Add a lightweight evaluation signal for the produced segmentation. The starter already has labels; use them in a way you can explain.
6. Add a simple inspection path for representative 2-D sections, such as a command, script, notebook, saved arrays, or images.
7. Record the commands you ran, failures you hit, and deployment decisions in `DECISIONS.md`.

## Data

This task is based on CREMI neuron segmentation data from serial-section electron microscopy. CREMI samples are volumetric images with neuron annotations. 

Start by looking at the files under `data/`, the pipeline code, and the tests. You may inspect individual 2-D sections, but the submission should make sense for volumetric data.

The `scripts/` directory contains optional helpers for inspecting or preparing small crops.
