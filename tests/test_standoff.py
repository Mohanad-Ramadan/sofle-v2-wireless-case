"""Tests for stepped standoff geometry."""
from build123d import Part
from sofle_case import constants as C
from sofle_case.standoffs import stepped_standoff


def test_returns_part():
    s = stepped_standoff(at=(50.0, 50.0))
    assert isinstance(s, Part)


def test_height():
    """Standoff spans FLOOR_THICKNESS (floor top) up to the pin top — which is
    STANDOFF_PIN_RECESS BELOW the plate underside, not level with it."""
    s = stepped_standoff(at=(50.0, 50.0))
    bb = s.bounding_box()
    assert abs(bb.min.Z - C.FLOOR_THICKNESS) < 0.01
    assert abs(bb.max.Z - (C.PLATE_SEAT_Z - C.STANDOFF_PIN_RECESS)) < 0.01


def test_pin_stops_short_of_the_plate():
    """THE PIN MUST NOT REACH THE PLATE. The plate's height is a hardware datum set by the
    switches (PCB_TOP_Z + MX_BODY_CLEAR); a pin that touched it would be a second datum for
    the same face, and the two only agree if MX_BODY_CLEAR is exact. It was out by 0.4-1.0 mm,
    the pins held the plate off the switches, and the printed sandwich would not shut.

    This is the assertion that keeps the pin a screw boss. A regression to a flush pin
    reintroduces the over-constraint silently — the geometry stays valid and every clearance
    test still passes, because nothing else measures this gap."""
    s = stepped_standoff(at=(50.0, 50.0))
    gap = C.PLATE_SEAT_Z - s.bounding_box().max.Z
    assert gap > 0.29, (
        f"standoff pin tops out {gap:.3f} mm below the plate — too little to absorb the "
        f"MX_BODY_CLEAR uncertainty band (3.40-4.00, held at {C.MX_BODY_CLEAR})"
    )
    assert abs(gap - C.STANDOFF_PIN_RECESS) < 0.01


def test_pin_is_solid_no_tap_bore():
    """SCREWLESS: the pin is a solid PCB-registration boss — the M2 self-tap bore is gone.
    Probe the pin axis just below the top; a Ø1.2 probe (narrower than the old Ø1.8 bore) must
    land in SOLID material. If a tap bore or any axial void creeps back, the probe falls into it
    and this fails."""
    from build123d import Solid
    s = stepped_standoff(at=(50.0, 50.0))
    pin_top = C.PLATE_SEAT_Z - C.STANDOFF_PIN_RECESS
    probe = Solid.make_cylinder(0.6, 1.0).translate((50.0, 50.0, pin_top - 1.0))
    inside = (s & probe).volume
    assert inside > 0.99 * probe.volume, (
        f"pin axis is not solid near the top ({inside:.3f} of {probe.volume:.3f} mm^3) — a tap "
        f"bore or void has crept back in"
    )


def test_lower_diameter():
    """At Z just above floor, OD should be STANDOFF_OD_LOWER."""
    s = stepped_standoff(at=(0.0, 0.0))
    bb = s.bounding_box()
    # XY half-extent at the widest cross-section is OD_LOWER/2
    assert abs((bb.max.X - bb.min.X) - C.STANDOFF_OD_LOWER) < 0.01
    assert abs((bb.max.Y - bb.min.Y) - C.STANDOFF_OD_LOWER) < 0.01


def test_centered_at_xy():
    s = stepped_standoff(at=(12.34, 56.78))
    bb = s.bounding_box()
    cx = (bb.min.X + bb.max.X) / 2
    cy = (bb.min.Y + bb.max.Y) / 2
    assert abs(cx - 12.34) < 0.01
    assert abs(cy - 56.78) < 0.01
