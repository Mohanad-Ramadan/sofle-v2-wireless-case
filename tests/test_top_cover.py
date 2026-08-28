"""Top cover (sandwich lid) tests."""
from build123d import Part, Solid
from sofle_case import constants as C
from tests.shared_builds import build_top_cover


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


def test_windows_carry_a_real_assembly_clearance():
    """Clearing the NOMINAL collar is not the claim that matters; surviving the tolerance
    stack is. This is the regression on ``COVER_WINDOW_OFFSET = 0.85``.

    That value gave a 15.70 mm window over a 15.60 mm collar — 0.05 mm/side — and it
    passed the nominal test above while the printed cover could not be fitted over the
    keyboard at all. The membrane has to swallow all 29 collars at once in the last
    millimetre of travel, and each collar can present ±0.2 mm off nominal before any FDM
    error: the plate floats ±0.1 mm on Ø3.9 pins in its Ø4.1 holes, and each switch floats
    ±0.1 mm in its own 14.0 mm plate cutout with a 13.8 mm lower housing. Printed windows
    also come out undersize. At 0.85, every one of the 29 windows bound on a collar
    oversized by only 0.10 mm."""
    from build123d import Axis, Solid
    from sofle_case.switch_phantom import _load_switch_positions
    stack = 0.2   # mm/side of assembly float, before any print error
    w = C.MX_TOP_HOUSING_W + 2 * stack
    cv = build_top_cover()
    switches = _load_switch_positions()
    binding = []
    for sw in switches:
        cx, cy = C.pcb_to_case(sw["x"], sw["y"])
        collar = Solid.make_box(w, w, C.COVER_THICKNESS).translate((-w / 2, -w / 2, 0.0))
        collar = collar.rotate(Axis.Z, sw["rot"]).translate((cx, cy, C.MAIN_RIM_Z))
        if (cv & collar).volume > 1e-4:
            binding.append(sw["name"])
    assert not binding, (
        f"{len(binding)}/{len(switches)} windows bind on a collar {stack} mm/side oversize "
        f"— no room for the assembly tolerance stack: {binding}")


def test_puller_notches_open_two_faces_per_switch(monkeypatch):
    """A switch puller grips the switch collar at the plate line; the flush window
    hugs it too tightly to admit a claw. Each MX switch must get a puller notch on
    BOTH its local ±Y faces so a claw-sized pocket reaches the plate in place.

    Force the feature on regardless of the shipped ``COVER_PULLER_NOTCH`` default so
    the notch geometry is always validated."""
    from build123d import BuildPart, Box, Locations, Location
    from sofle_case.top_cover import _load_switch_positions
    # Fresh, UNCACHED build: the monkeypatched constant must take effect here, and the
    # shared cache (populated with the shipped default) must not be polluted by it.
    from sofle_case.top_cover import build_top_cover as build_fresh_top_cover
    monkeypatch.setattr(C, "COVER_PULLER_NOTCH", True)
    cv = build_fresh_top_cover()
    z = C.MAIN_RIM_Z + C.COVER_THICKNESS / 2
    blocked = 0
    for sw in _load_switch_positions():
        cx, cy = C.pcb_to_case(sw["x"], sw["y"])
        for sign in (1.0, -1.0):
            # a claw-sized probe just past the 7.8 mm collar, at plate level
            with BuildPart() as bp:
                with Locations(Location((cx, cy, z), (0, 0, sw["rot"]))):
                    with Locations((0.0, sign * 8.3, 0.0)):
                        Box(3.0, 1.0, C.COVER_THICKNESS)
            if (cv & bp.part).volume > 0.05:
                blocked += 1
    assert blocked == 0, f"{blocked} switch faces still block a puller claw"


def test_keycap_headroom():
    """Cover top must stay below the keycap skirt at full press so it never blocks a
    keypress.

    KEYCAP_SKIRT_CLEAR_AT_FULL_PRESS (1.5 mm) is a community/field figure, not a Cherry
    datasheet spec — see the note in constants.py above its definition. Treat the margin
    this asserts as tight, not comfortable: this build already hit contact once at this
    clearance."""
    cover_top = C.MAIN_RIM_Z + C.COVER_THICKNESS
    full_press_skirt = C.MAIN_RIM_Z + C.KEYCAP_SKIRT_CLEAR_AT_FULL_PRESS
    assert cover_top < full_press_skirt, "cover top would touch the keycap skirt at full press"


def test_no_screw_holes():
    """SCREWLESS: the cover has NO M2 clearance holes — the membrane is SOLID at every standoff.
    A thin probe at each standoff must be mostly blocked by membrane material; a hole creeping
    back would let it pass and fail this."""
    cv = build_top_cover()
    for hx, hy in C.MOUNTING_HOLES:
        cx, cy = C.pcb_to_case(hx, hy)
        probe = Solid.make_cylinder(1.0, C.COVER_THICKNESS).translate((cx, cy, C.MAIN_RIM_Z))
        assert (cv & probe).volume > 0.5 * probe.volume, (
            f"membrane not solid at standoff PCB ({hx}, {hy}) — a screw hole has crept back")
