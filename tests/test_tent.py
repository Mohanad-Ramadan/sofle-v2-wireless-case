"""Integrated tent wedge on the BOTTOM case — the thing that actually tilts the keyboard.

Modelled on the WOBKEY Crush 80: top case is a constant-section shell, bottom case is a
wedge, and the whole assembly tips forward on it, so the parting line between them runs
parallel to the KEYS rather than to the desk.

The wedge is ADDED, never cut, and that is the load-bearing design decision here. Cutting
the bottom case is what would wreck the Z ladder — the floor is 6.3 mm and only 2.0 mm of it
is free, because the battery pocket's floor spans Y 30.8-103.8 through the middle. So these
tests care about two things above all: the tilt is real, and NOTHING above the wedge moved."""
import math

from build123d import Solid
from sofle_case import constants as C
from sofle_case.canopy import CANOPY_RIDGE_TOP_Z, canopy_ridge_top_z
from sofle_case.case import (ground_face, tent_ground_z, tent_plane, tent_wedge,
                             wedge_deep_z)
from tests.shared_builds import build_bottom_part, build_top_part
from sofle_case.tray import offset_extruded

OUTER = C.WALL_THICKNESS + C.PCB_XY_CLEARANCE


def _solid_at(part, x, y, z, s=0.1):
    """Probe. Short in Y — the ground face is tilted, so a long probe spans height."""
    box = Solid.make_box(s, 0.25, s).translate((x - s / 2, y - 0.125, z - s / 2))
    return (part & box).volume > 1e-9


# --------------------------------------------------------------------------- the tilt

def test_wedge_thickness_follows_the_tent_angle():
    """Thin at the south, thick at the north, at exactly TENT_ANGLE_DEG in between."""
    t = math.tan(math.radians(C.TENT_ANGLE_DEG))
    assert abs(-tent_ground_z(0.0) - C.TENT_WEDGE_MIN_H) < 1e-9
    assert abs(-tent_ground_z(C.OUTER_DEPTH) - C.TENT_WEDGE_MAX_H) < 1e-9
    # the part only reaches the PLATE's north extent, short of the tub outline
    assert -C.TENT_WEDGE_MAX_H < wedge_deep_z() < -C.TENT_WEDGE_MIN_H
    assert abs(C.TENT_RISE - C.OUTER_DEPTH * t) < 1e-9
    assert C.TENT_WEDGE_MAX_H > C.TENT_WEDGE_MIN_H, "the wedge is upside down"


def test_ground_face_is_one_exact_plane_pitched_the_right_way():
    """A single planar face, pitched front-to-back only. Two faces, a spline, or any roll
    component and the keyboard sits on points instead of standing flat and square."""
    face = ground_face(build_bottom_part("right"))
    assert face is not None, "no ground face — the wedge did not cut through"
    assert str(face.geom_type) == "GeomType.PLANE", f"ground face is {face.geom_type}"
    n = face.normal_at(face.center())
    pitch = math.degrees(math.atan2(abs(n.Y), abs(n.Z)))
    assert abs(pitch - C.TENT_ANGLE_DEG) < 1e-6, f"stands at {pitch:.4f}°, want {C.TENT_ANGLE_DEG}"
    assert abs(n.X) < 1e-9, f"ground face carries {n.X:.2e} of roll — it must pitch only"


def test_nothing_pokes_below_the_ground_plane():
    """Everything sits ON the plane, nothing through it. One stray vertex below becomes the
    only contact point and the keyboard rocks on it."""
    o, n = tent_plane()
    for side in ("right", "left"):
        verts, _f = build_bottom_part(side).tessellate(0.2)
        worst = min((v.X - o[0]) * n[0] + (v.Y - o[1]) * n[1] + (v.Z - o[2]) * n[2] for v in verts)
        assert worst > -1e-4, f"{side}: geometry dips {-worst:.4f} mm through the ground plane"


def test_contact_is_the_whole_footprint():
    """The case rests on the wedge's full plan area, so it cannot rock and needs no coplanarity
    proof — unlike the four inset riser feet this design replaced."""
    face = ground_face(build_bottom_part("right"))
    assert face.area > 10000.0, f"ground face is only {face.area:.0f} mm² — that is not the footprint"
    assert len(face.inner_wires()) == len(C.FOOT_POSITIONS), \
        "expected exactly the foot seats as holes in the ground face"


# ------------------------------------------------------- nothing above the wedge moved

def test_top_case_is_untouched_above_z0():
    """The whole point of adding rather than cutting: everything the internals care about is
    unmoved. The ceiling is still THIS half's canopy ridge (per-half since the ridge-per-half
    fix — right and left no longer share one number), and every facet, the rabbet and the
    membrane sit where they were.

    Below Z=0 the tub DOES now change — it carries the skin extension that runs just above the
    desk over the southern stretch (see test_seam.py). That is additive too, and costs no height."""
    for side in ("right", "left"):
        bb = build_top_part(side).bounding_box()
        assert abs(bb.max.Z - canopy_ridge_top_z(side)) < 0.01, f"{side}: tub ceiling moved"
        assert bb.min.Z > wedge_deep_z(), f"{side}: tub reaches below the wedge's floor"


def test_the_z_ladder_is_unchanged():
    """The stack the internals depend on. A tilt paid for by cutting the bottom case would
    have moved every one of these — that is why the wedge is additive."""
    assert C.FLOOR_THICKNESS == 6.3
    assert C.PCB_SEAT_Z == C.FLOOR_THICKNESS + C.STANDOFF_SHOULDER_H
    assert C.PLATE_SEAT_Z == C.PCB_TOP_Z + C.MX_BODY_CLEAR
    assert C.COVER_TOP_Z == C.MAIN_RIM_Z + C.COVER_THICKNESS
    assert C.SEAM_LEDGE_Z == C.FLOOR_THICKNESS


def test_battery_floor_is_still_the_full_2mm():
    """The constraint that forced 'add, don't cut'. Pinned so nobody spends it later."""
    from sofle_case.battery import battery_pocket
    assert abs(battery_pocket().bounding_box().min.Z - 2.0) < 1e-6


def test_total_height_is_exactly_the_wedge():
    """The case grew by the wedge and by nothing else — no accidental extra anywhere.

    The floor lands a hair ABOVE -TENT_WEDGE_MAX_H, never below: the elephant-foot
    counter-chamfer trims the ground rim back by BOTTOM_CHAMFER, and stepping 0.5 mm inboard
    on a 2° plane lifts the deepest surviving point by 0.5·tan(2°) ≈ 0.017 mm. Asserting
    equality here is how the ground-face selector bug hid — the chamfer was landing on a foot
    seat instead of the rim, so the number came out suspiciously exact."""
    top, bottom = build_top_part("right"), build_bottom_part("right")
    tb, bb = top.bounding_box(), bottom.bounding_box()
    lo, hi = min(tb.min.Z, bb.min.Z), max(tb.max.Z, bb.max.Z)
    lift = C.BOTTOM_CHAMFER * math.tan(math.radians(C.TENT_ANGLE_DEG))
    assert wedge_deep_z() <= lo <= wedge_deep_z() + lift + 1e-3, \
        f"floor at {lo:.4f}, expected {wedge_deep_z():.4f} + up to {lift:.4f} of chamfer"
    assert (hi - lo) <= CANOPY_RIDGE_TOP_Z + C.TENT_WEDGE_MAX_H + 1e-3, \
        f"total {hi - lo:.3f} exceeds ridge + wedge — something else grew"


# ------------------------------------------------------------------- fit and finish

def test_wedge_is_inset_behind_the_tub_skin():
    """Deliberately "skinny": the wedge rides the PLATE's rim profile, so the bottom case sits
    SEAM_SKIN + SEAM_FIT_CLEAR back from the tub's outer face and shows as a recessed plinth.

    That inset is what keeps this cheap. A flush wedge would have to chase the tub's REAL
    footprint — the +Y relief bump squares the NW corner off proud of the nominal offset and
    carries a fillet — which meant sampling a whole built tray inside every bottom part.

    SEAM_NORTH_RISE_FRAC does not touch this. It cuts the TUB back and nothing else, so lifting
    the parting line deepens the recess rather than filling it: the bottom's outline is the same
    at every setting of the dial."""
    top, bottom = build_top_part("right"), build_bottom_part("right")
    tb, bb = top.bounding_box(), bottom.bounding_box()
    inset = C.SEAM_SKIN + C.SEAM_FIT_CLEAR
    for lo_t, lo_b in ((tb.min.X, bb.min.X), (tb.min.Y, bb.min.Y)):
        assert 0.5 < lo_b - lo_t <= inset + 1e-6, \
            f"bottom case inset {lo_b - lo_t:.2f} mm, expected up to {inset:.2f}"
    assert bb.max.X < tb.max.X and bb.max.Y < tb.max.Y, "bottom case is not inset on all sides"
    # The tub's skin descends past the wedge over the southern stretch, but always OUTBOARD of
    # it — that inset is exactly the room the skin drops through. They must never touch.
    assert (build_top_part("right") & bottom).volume < 1e-6, "skin and wedge collide"


def test_parts_still_close_and_the_plate_still_inserts():
    """No interference, and the plate's straight-up insertion column is still clear."""
    top, bottom = build_top_part("right"), build_bottom_part("right")
    assert (top & bottom).volume < 1e-6, "top and bottom overlap — they will not close"
    rim_outer = C.PCB_XY_CLEARANCE + C.SEAM_RIM_THK
    column = offset_extruded(rim_outer, -20.0, C.SEAM_LEDGE_Z)
    assert (top & column).volume < 1e-6, "the tub intrudes on the plate's insertion column"


def test_both_halves_are_single_solids():
    """The wedge fuses to the plate across a shared Z=0 plane — a coincident-face union OCC
    is not always happy about. If it ever splits, this catches it before the slicer does."""
    for side in ("right", "left"):
        assert len(build_bottom_part(side).solids()) == 1, f"{side} bottom fractured"
        assert len(build_top_part(side).solids()) == 1, f"{side} top fractured"


def test_wedge_alone_is_a_clean_solid():
    """Guards the wedge builder itself, independent of everything it gets fused to."""
    w = tent_wedge()
    assert len(w.solids()) == 1
    bb = w.bounding_box()
    assert abs(bb.max.Z) < 1e-6, f"wedge top should sit on Z=0, got {bb.max.Z:.4f}"
    assert abs(bb.min.Z - wedge_deep_z()) < 1e-6
