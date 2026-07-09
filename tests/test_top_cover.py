"""Top cover (sandwich lid) tests."""
from build123d import Part, Solid
from sofle_case import constants as C
from sofle_case.top_cover import build_top_cover


def test_returns_single_solid():
    cv = build_top_cover()
    assert isinstance(cv, Part)
    assert len(cv.solids()) == 1, f"cover has {len(cv.solids())} solids; expected 1"


def test_sits_on_plate_top():
    """Cover spans MAIN_RIM_Z (plate top) up by COVER_THICKNESS — a thin lid."""
    bb = build_top_cover().bounding_box()
    assert abs(bb.min.Z - C.MAIN_RIM_Z) < 0.01
    assert abs(bb.max.Z - (C.MAIN_RIM_Z + C.COVER_THICKNESS)) < 0.01


def test_footprint_matches_plate():
    """Cover mimics the switch-plate outline (143.5 x 115.5), centred in the case."""
    bb = build_top_cover().bounding_box()
    assert abs((bb.max.X - bb.min.X) - 143.5) < 0.5
    assert abs((bb.max.Y - bb.min.Y) - 115.5) < 0.5
    assert abs((bb.min.X + bb.max.X) / 2 - C.OUTER_WIDTH / 2) < 0.5


def test_windows_clear_all_switch_housings():
    """Every switch window must clear the 15.6 mm MX top housing — the cover must
    not intersect any switch body (incl. the rotated thumb switches)."""
    from sofle_case.switch_phantom import build_switch_phantom
    cv = build_top_cover()
    housings = build_switch_phantom()
    assert (cv & housings).volume < 1e-3, "cover overlaps a switch housing — window too small"


def test_keycap_headroom():
    """Cover top must stay below the keycap skirt at full press (~1.5 mm above the
    plate) so it never blocks a keypress."""
    cover_top = C.MAIN_RIM_Z + C.COVER_THICKNESS
    full_press_skirt = C.MAIN_RIM_Z + 1.5   # measured skirt-to-plate clearance at full press
    assert cover_top < full_press_skirt, "cover top would touch the keycap skirt at full press"


def test_screw_holes_open():
    """Each standoff position must be a clear M2 hole through the cover."""
    cv = build_top_cover()
    for hx, hy in C.MOUNTING_HOLES:
        cx, cy = C.pcb_to_case(hx, hy)
        # a thin pin the size of the M2 shaft must pass straight through
        pin = Solid.make_cylinder(
            C.COVER_SCREW_CLEARANCE_DIA / 2 - 0.1, C.COVER_THICKNESS + 0.2
        ).translate((cx, cy, C.MAIN_RIM_Z - 0.1))
        assert (cv & pin).volume < 1e-3, f"screw hole blocked at PCB ({hx}, {hy})"
