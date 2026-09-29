import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.tiling import Tile, plan_tiles


def test_plan_tiles_covers_volume_once():
    tiles = plan_tiles((5, 6, 7), (3, 4, 4), (1, 1, 1))
    assert tiles
    covered = set()
    for tile in tiles:
        assert isinstance(tile, Tile)
        for axis, (read, limit) in enumerate(zip(tile.read_slices, (3, 4, 4))):
            assert read.stop - read.start <= limit, (
                f"axis {axis} read slice {read} is larger than max tile size {limit}"
            )
        for z in range(tile.write_slices[0].start, tile.write_slices[0].stop):
            for y in range(tile.write_slices[1].start, tile.write_slices[1].stop):
                for x in range(tile.write_slices[2].start, tile.write_slices[2].stop):
                    point = (z, y, x)
                    assert point not in covered, f"voxel {point} was written more than once"
                    covered.add(point)
    assert len(covered) == 5 * 6 * 7, "write slices did not cover the full volume"


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__]))
