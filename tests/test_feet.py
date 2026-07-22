"""Anti-slip rubber-foot seats on the underside of the bottom plate."""
import math
from build123d import Solid
from sofle_case import constants as C
from sofle_case.case import build_bottom_part


def _solid_at(part, x, y, z, s=0.3):
    # Small probe (0.3 mm) so it resolves the shallow FOOT_DEPTH seat without poking
    # above the seat floor into the solid plate.
    probe = Solid.make_box(s, s, s).translate((x - s / 2, y - s / 2, z - s / 2))
    return (part & probe).volume > 1e-6


def test_four_foot_seats_open_the_bottom_face():
    """Each foot position is recessed at the Z=0 underside (air just inside the seat)
    yet solid deeper up (the seat is shallow, it does not perforate the plate)."""
    part = build_bottom_part("right")
    for x, y in C.FOOT_POSITIONS:
        assert not _solid_at(part, x, y, 0.3), f"foot seat at ({x},{y}) not cut at the bottom face"
        assert _solid_at(part, x, y, C.FOOT_DEPTH + 1.0), f"plate perforated above foot seat ({x},{y})"


def test_foot_seat_depth():
    """Seat is FOOT_DEPTH deep: solid appears just above the seat floor, not below it."""
    part = build_bottom_part("right")
    x, y = C.FOOT_POSITIONS[0]
    assert not _solid_at(part, x, y, C.FOOT_DEPTH - 0.3), "seat shallower than FOOT_DEPTH"
    assert _solid_at(part, x, y, C.FOOT_DEPTH + 0.3), "seat deeper than FOOT_DEPTH"


def test_full_foot_footprint_on_solid_plate():
    """The whole Ø FOOT_DIA seat lands on plate material (no seat hangs off the outline)."""
    part = build_bottom_part("right")
    r = C.FOOT_DIA / 2
    z = C.FOOT_DEPTH + 1.0  # just above the seat, in solid plate
    for x, y in C.FOOT_POSITIONS:
        rim = [(x + r * math.cos(a), y + r * math.sin(a))
               for a in (i * math.pi / 4 for i in range(8))]
        for px, py in rim:
            assert _solid_at(part, px, py, z), f"foot seat at ({x},{y}) overhangs the plate edge"


def test_feet_present_on_both_sides():
    """Feet survive the left-mirror (subtracted before the mirror), so both halves grip."""
    for side in ("right", "left"):
        part = build_bottom_part(side)
        cut = sum(1 for x, y in _mirrored_positions(side) if not _solid_at(part, x, y, 0.3))
        assert cut == len(C.FOOT_POSITIONS), f"{side}: only {cut}/{len(C.FOOT_POSITIONS)} feet cut"


def _mirrored_positions(side):
    if side == "right":
        return C.FOOT_POSITIONS
    axis = C.OUTER_WIDTH / 2
    return [(2 * axis - x, y) for x, y in C.FOOT_POSITIONS]
