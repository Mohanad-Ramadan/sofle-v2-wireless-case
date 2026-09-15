"""Underside rubber-foot recesses."""
import math

from build123d import Solid

from sofle_case import constants as C
from tests.shared_builds import build_case_half


def _solid_at(part, x, y, z, size=0.25):
    probe = Solid.make_box(size, size, size).translate(
        (x - size / 2, y - size / 2, z - size / 2))
    return (part & probe).volume > 1e-6


def test_four_foot_recesses_open_at_z_zero():
    for side in ("right", "left"):
        part = build_case_half(side)
        positions = C.FOOT_POSITIONS if side == "right" else tuple(
            (C.OUTER_WIDTH - x, y) for x, y in C.FOOT_POSITIONS)
        for x, y in positions:
            assert not _solid_at(part, x, y, 0.25)
            assert _solid_at(part, x, y, C.FOOT_DEPTH + 0.25)
            for angle in (i * math.pi / 4 for i in range(8)):
                edge_x = x + C.FOOT_DIA / 2 * math.cos(angle)
                edge_y = y + C.FOOT_DIA / 2 * math.sin(angle)
                assert _solid_at(part, edge_x, edge_y, C.FOOT_DEPTH + 0.25), (
                    f"{side} foot recess at ({x}, {y}) overhangs the case"
                )
