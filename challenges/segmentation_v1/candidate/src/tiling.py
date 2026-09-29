from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Tile:
    read_slices: tuple[slice, slice, slice]
    write_slices: tuple[slice, slice, slice]


def plan_tiles(
    shape: tuple[int, int, int],
    max_tile_shape: tuple[int, int, int],
    overlap: tuple[int, int, int],
) -> list[Tile]:
    # Research prototype: works for toy volumes, but ignores max_tile_shape and overlap.
    # Replace this with bounded reads and non-overlapping writes for production-scale data.
    return [Tile(tuple(slice(0, size) for size in shape), tuple(slice(0, size) for size in shape))]
