"""Does the case actually SHUT over the keyboard?

Every other clearance test in this suite asks a local question — does this cutter clear that
body, is this pocket deep enough. The printed case failed three times anyway, because closure
is a global property and nothing asserted it:

  * the encoder plateau clipped the EC11 body            (fixed, 7a54949)
  * the cover windows bound on 29 switch collars         (fixed, d60d25d)
  * the plate rode on the switches, not the standoffs    (fixed, MX_BODY_CLEAR + PIN_RECESS)
  * the battery JST fouled the cover by 34.2 mm^3        (fixed by moving it under the PCB)

Each one held the TOP off the switch plate on its own, and each one passed every test that
existed at the time. All four were found by printing the case, not by running the suite.

The JST is the sharpest lesson of the four. It was not a number that drifted — it was a part with
NO datum anywhere, absent from the CPL (J2 is footprinted as a generic 1x03 socket) and present in
the source only as a sentence in ``canopy.py`` promising the ramp "starts climbing early enough to
clear the JST beneath it". Nothing could check a claim about a part the model did not represent.
A phantom that does not exist cannot foul anything, and that reads exactly like success.

This module asserts the property directly: with every piece of hardware at its modelled height,
no hardware may touch either printed part, and it must not merely miss — it must miss with room
to spare. Two failure modes are separated on purpose:

  interference  a body and a part overlap. The case cannot close. Hard failure.
  coincidence   a body and a part touch at exactly 0.000 mm^3. The case "closes" in CAD and
                jams in PLA, because a printed face is never where the model puts it. Zero
                interference and real clearance are different claims and are tested separately.

STANDING CAVEAT: every number here is only as good as the phantom it measures against. A body
modelled too short reads clear against a case that the real part fouls, and no assertion in this
file can see that. The SK12 slide-switch dims in particular are ASSUMED, not measured.
"""
from typing import cast

import pytest
from build123d import Part, Plane, Pos, Solid, mirror

from sofle_case import constants as C
from sofle_case import knob as K
from sofle_case.pcb_phantom import (
    _jst_body,
    _mcu_block,
    _pcb_plate,
    _slide_switch_body,
    _usb_c_stub,
)
from sofle_case.plate_phantom import build_plate_phantom
from sofle_case.switch_phantom import build_switch_phantom
from tests.shared_builds import build_bottom_part, build_top_part

# Minimum air at every hardware interface. Not a style number: an FDM face lands within roughly
# +/-0.2 mm of nominal, and this stack puts two printed faces and one FR4 face in series, so a
# design that clears by less than this is relying on the printer.
MIN_CLEARANCE = 0.3

# An obstruction has THICKNESS. When a lifted body's face grazes a cut wall, OCC hands back a
# sliver of near-zero width that still carries a positive volume — one seen while sizing the slide
# pocket was 0.01 mm wide and 0.006 mm³, yet a 0.05 mm material probe swept across the same band
# read 0.0% solid the whole way. Thresholding on volume alone cannot tell that apart from a real
# 0.006 mm³ nub, so these tests measure the overlap's THINNEST dimension instead. Below one FDM
# extrusion width there is nothing a printer could lay down, so there is nothing to collide with.
MIN_OBSTRUCTION = 0.05

# Solid floor that must survive beneath the JST pocket. Set against BATTERY_FLOOR_BASE (2.0), which
# is what the battery pocket keeps — the JST pocket goes deeper, so it gets the same duty of care
# rather than a looser one just because the wedge happens to be generous where it lands.
JST_MIN_FLOOR_UNDER = 2.0


def _mirrored(part: Part, side: str) -> Part:
    """Phantoms are authored in RIGHT-hand coords, as the case is; the left half is the mirror."""
    if side != "left":
        return part
    return cast(Part, Pos(C.OUTER_WIDTH / 2, 0, 0) * mirror(
        Pos(-C.OUTER_WIDTH / 2, 0, 0) * part, about=Plane.YZ))


def _hardware(side: str) -> list[tuple[str, Part]]:
    return [
        ("PCB", _mirrored(_pcb_plate(), side)),
        ("FR4 switch plate", _mirrored(build_plate_phantom(), side)),
        ("MX switches", _mirrored(build_switch_phantom(), side)),
        ("nice!nano", _mirrored(_mcu_block(), side)),
        ("USB-C jack", _mirrored(_usb_c_stub(side), side)),
        ("slide switch", _mirrored(_slide_switch_body(), side)),
        ("battery JST", _mirrored(_jst_body(), side)),
        ("EC11 knob", _mirrored(K.place_knob(bottomed=True), side)),
    ]


def _solid_at(part: Part, x: float, y: float, z: float, s: float = 0.3) -> bool:
    probe = Solid.make_box(s, s, s).translate((x - s / 2, y - s / 2, z - s / 2))
    hit = part & probe
    return hit is not None and cast(Part, hit).volume > 1e-6


def _solid_run_down(part: Part, x: float, y: float, z_start: float, z_min: float,
                    step: float = 0.1) -> float:
    """Thickness of the first CONTIGUOUS band of material found walking DOWN from ``z_start``.

    Contiguous on purpose. Taking ``z_start`` minus the deepest solid point anywhere below would
    count voids as material and report a floor that is not there — which is the exact class of
    false pass this module exists to stop.

    Probes the built solid rather than computing a thickness from the constants that produced it;
    the material here comes from the tent wedge, not from the floor constants, so arithmetic over
    those constants would be measuring the wrong feature.
    """
    z = z_start
    while z > z_min and not _solid_at(part, x, y, z):
        z -= step
    if z <= z_min:
        return 0.0
    top = z
    while z > z_min and _solid_at(part, x, y, z):
        z -= step
    return top - z


def _overlap(part: Part, body: Part) -> tuple[float, float, str]:
    """(volume, thinnest dimension, where) of the intersection. Empty reads (0.0, 0.0, "")."""
    hit = part & body
    if hit is None or cast(Part, hit).volume <= 1e-9:
        return 0.0, 0.0, ""
    solid = cast(Part, hit)
    bb = solid.bounding_box()
    thin = min(bb.max.X - bb.min.X, bb.max.Y - bb.min.Y, bb.max.Z - bb.min.Z)
    where = (f"x {bb.min.X:.2f}..{bb.max.X:.2f}  y {bb.min.Y:.2f}..{bb.max.Y:.2f}  "
             f"z {bb.min.Z:.2f}..{bb.max.Z:.2f}")
    return solid.volume, thin, where


@pytest.mark.parametrize("side", ["right", "left"])
def test_no_hardware_fouls_either_printed_part(side):
    """Nothing the user installs may overlap either printed part at its measured height."""
    top, bottom = build_top_part(side), build_bottom_part(side)
    offenders = []
    for name, body in _hardware(side):
        for part_name, part in (("TOP", top), ("BOTTOM", bottom)):
            vol, thin, where = _overlap(part, body)
            if thin > MIN_OBSTRUCTION:
                offenders.append(
                    f"{name} x {part_name}: {vol:.3f} mm^3, {thin:.3f} mm thick, at {where}")
    assert not offenders, "hardware fouls the printed case:\n  " + "\n  ".join(offenders)


@pytest.mark.parametrize("side", ["right", "left"])
def test_hardware_clearance_is_real_not_coincident(side):
    """Raise every body by MIN_CLEARANCE and require it to STAY clear.

    A body that passes the interference test but fails this one is touching, not clearing —
    it closes in CAD and jams in PLA. Excludes the switch plate, whose top face the cover
    deliberately sits on; that interface is the assembly's Z datum and is asserted separately
    by test_seam_ledge_gap_absorbs_the_plate_stack.
    """
    top, bottom = build_top_part(side), build_bottom_part(side)
    tight = []
    for name, body in _hardware(side):
        if name == "FR4 switch plate":
            continue
        lifted = cast(Part, Pos(0, 0, MIN_CLEARANCE) * body)
        for part_name, part in (("TOP", top), ("BOTTOM", bottom)):
            vol, thin, where = _overlap(part, lifted)
            if thin > MIN_OBSTRUCTION:
                tight.append(f"{name} x {part_name}: fouls by {vol:.3f} mm^3 ({thin:.3f} mm "
                             f"thick) at {where} when raised {MIN_CLEARANCE} mm — nominal "
                             f"clearance is under that")
    assert not tight, (
        "hardware clears by less than " + f"{MIN_CLEARANCE} mm:\n  " + "\n  ".join(tight))


@pytest.mark.parametrize("side", ["right", "left"])
def test_the_floor_carries_real_material_under_the_jst_pocket(side):
    """The JST pocket is deep, and what stops it becoming a hole is the tent wedge, not the floor.

    ``JST_POCKET_FLOOR_Z`` sits 0.70 mm above Z=0 — against the nominal 6.3 mm floor alone that
    would be a near-breakthrough. It is safe only because the wedge carries ~14.5 mm of material
    here. That margin belongs to a DIFFERENT feature than the one that consumes it, so it is
    asserted by probing the built solid rather than by arithmetic over the constants that built
    the pocket. If the tent angle, the wedge, or the pocket depth ever move, this is what notices.
    """
    bottom = build_bottom_part(side)
    x, y = C.pcb_to_case(*C.JST_POS)
    if side == "left":
        x = C.OUTER_WIDTH - x          # phantoms are right-handed; so is this point

    thickness = _solid_run_down(bottom, x, y, C.JST_POCKET_FLOOR_Z - 0.05, -20.0)
    assert thickness >= JST_MIN_FLOOR_UNDER, (
        f"only {thickness:.2f} mm of material survives under the JST pocket at case "
        f"({x:.2f}, {y:.2f}); {JST_MIN_FLOOR_UNDER} mm is the floor. The pocket bottoms at "
        f"Z {C.JST_POCKET_FLOOR_Z:.2f} and relies on the tent wedge to be there — check whether "
        f"the wedge moved, not the pocket"
    )


@pytest.mark.parametrize("mount", ["east", "west"])
def test_either_jst_mounting_fits_the_pocket(mount):
    """The connector may sit on either pair of holes, so the pocket must take either.

    The middle hole is B+ and both outer holes are GND, which makes the part electrically
    reversible on the board. That freedom is invisible from the geometry — nothing downstream can
    tell you the connector was ALLOWED to move — so a pocket cut to whichever pair was soldered
    first would silently turn a free choice into a permanent one, and the first anybody heard of
    it would be a connector that no longer drops in after a reprint.

    The phantom draws only one position at a time, so the default clash sweep exercises exactly
    one of the two. This is the other half.
    """
    from sofle_case.battery import _jst_pocket_bounds, jst_pocket
    from sofle_case.pcb_phantom import _jst_body

    x_lo, x_hi, y_lo, y_hi = _jst_pocket_bounds()
    bb = _jst_body(mount).bounding_box()
    assert x_lo <= bb.min.X and bb.max.X <= x_hi, (
        f"{mount} mounting spans X {bb.min.X:.2f}..{bb.max.X:.2f}, outside the pocket's "
        f"{x_lo:.2f}..{x_hi:.2f}")
    assert y_lo <= bb.min.Y and bb.max.Y <= y_hi, (
        f"{mount} mounting spans Y {bb.min.Y:.2f}..{bb.max.Y:.2f}, outside the pocket's "
        f"{y_lo:.2f}..{y_hi:.2f}")

    # And it must clear in the round, not just by bbox — the pocket has filleted corners.
    #
    # Only the part BELOW the floor's top face is the pocket's problem. The connector spans
    # Z 2.30..8.80 and the pocket stops at FLOOR_THICKNESS (6.30); the top 2.5 mm lives in the
    # air gap under the PCB (STANDOFF_SHOULDER_H), which is not a pocket at all. Comparing the
    # whole body against the pocket reports that gap as 286 mm³ of interference — a false
    # failure that would push someone into deepening a pocket that is already correct.
    floor_and_below = Solid.make_box(400, 400, 60).translate((-100, -100, C.FLOOR_THICKNESS - 60))
    sunk = cast(Part, _jst_body(mount) & floor_and_below)
    outside = cast(Part, sunk - jst_pocket())
    assert outside.volume < 1e-6, (
        f"{mount} mounting leaves {outside.volume:.3f} mm³ of connector outside the pocket below "
        f"the floor line — the corner fillets are eating it")


def test_the_wire_channel_actually_joins_the_two_pockets():
    """A channel that stops short of either pocket is a groove in the floor, not a wire route.

    All three recesses are separate cutters and nothing forces them to meet; abutting faces can
    read as non-intersecting and the render would show an open path the leads cannot take.

    Tested by BOOLEAN INTERSECTION rather than by comparing bounding boxes. The channel runs
    diagonally, so its bbox spans ground it never actually occupies — a bbox overlap would report
    a join that is not there, which is the failure this test exists to catch.
    """
    from sofle_case.battery import battery_pocket, jst_pocket, jst_wire_channel

    channel = jst_wire_channel()
    for name, pocket in (("JST pocket", jst_pocket()), ("battery pocket", battery_pocket())):
        hit = channel & pocket
        vol = cast(Part, hit).volume if hit is not None else 0.0
        assert vol > 1.0, (
            f"wire channel meets the {name} in {vol:.4f} mm³ — they do not overlap, so the leads "
            f"would have to cross solid floor between them")


def test_the_wire_channel_misses_every_standoff():
    """The routing is a clearance decision, not a preference — this is what records it.

    A run south of the JST pocket passes 0.46 mm from the standoff at case (53.32, 58.79), inside
    the standoff's own wall. Nothing in the geometry stops someone re-routing there to shorten
    the leads.

    Measured perpendicular to EVERY LEG of the real route. The channel is a hook, so a check
    against its bounding box would clear standoffs it actually passes close to and flag ones it
    never goes near — the bbox covers ground the path does not occupy.
    """
    import math
    from itertools import pairwise

    from sofle_case.battery import jst_channel_path

    pts = jst_channel_path()
    reach = C.STANDOFF_OD_LOWER / 2 + C.JST_CHANNEL_W / 2

    def _leg_gap(cx, cy, ax, ay, tx, ty):
        vx, vy = tx - ax, ty - ay
        t = max(0.0, min(1.0, ((cx - ax) * vx + (cy - ay) * vy) / (vx * vx + vy * vy)))
        return math.dist((cx, cy), (ax + t * vx, ay + t * vy)) - reach

    for hx, hy in C.MOUNTING_HOLES:
        cx, cy = C.pcb_to_case(hx, hy)
        gap = min(_leg_gap(cx, cy, *a, *b) for a, b in pairwise(pts))
        assert gap >= 1.0, (
            f"standoff at case ({cx:.2f}, {cy:.2f}) is {gap:.2f} mm from the wire channel — it "
            f"cuts into the base. Route: {[(round(x, 1), round(y, 1)) for x, y in pts]}")


def test_the_floor_survives_along_the_whole_wire_channel():
    """The channel is as deep as the pockets now, and it crosses most of the case to get there.

    Depth was previously sized to the wire (2.5 mm); it is now flush with the JST pocket at 4.50,
    and the route hooks north, east, south and east again for ~94 mm. That is a lot of floor to
    remove in places nobody probed — the material under it comes from the tent wedge, which is
    thinnest at the SOUTH, exactly where the battery end of this channel lands.
    """
    from itertools import pairwise

    from sofle_case.battery import jst_channel_path

    bottom = build_bottom_part("right")
    pts = jst_channel_path()
    thin = []
    for (ax, ay), (tx, ty) in pairwise(pts):
        for i in range(5):
            f = i / 4
            x, y = ax + (tx - ax) * f, ay + (ty - ay) * f
            t = _solid_run_down(bottom, x, y, C.JST_CHANNEL_FLOOR_Z - 0.05, -20.0)
            if t < JST_MIN_FLOOR_UNDER:
                thin.append(f"({x:.1f}, {y:.1f}): {t:.2f} mm")
    assert not thin, (
        "the wire channel leaves less than "
        f"{JST_MIN_FLOOR_UNDER} mm of floor beneath it at:\n  " + "\n  ".join(thin))


def test_seam_ledge_gap_absorbs_the_plate_stack():
    """The seam ledge must not become the thing that stops the case closing.

    The TOP's height is set by the plate stack — standoff shoulder, PCB, MX gap, plate — and
    the ledge has to stay clear of the bottom's rim through all of it. Working the chain in the
    bottom's frame, where its floor top and rim top are both SEAM_LEDGE_Z:

        bottom rim top  -> cover underside = STANDOFF_SHOULDER_H + PCB_THICKNESS
                                             + MX_BODY_CLEAR + PLATE_THICKNESS
        ledge face      -> cover underside = MAIN_RIM_Z - (SEAM_LEDGE_Z + SEAM_LEDGE_CLEAR)

    The difference is the gap. It reduces to SEAM_LEDGE_CLEAR exactly when the model's
    MX_BODY_CLEAR equals the real one — and it shrinks 1:1 as the real gap runs SMALLER than
    modelled, which is the direction that jams the case. The assertion is that the remaining
    margin covers a printed part's error, not merely that the arithmetic is positive.
    """
    stack = (C.STANDOFF_SHOULDER_H + C.PCB_THICKNESS + C.MX_BODY_CLEAR + C.PLATE_THICKNESS)
    to_ledge = C.MAIN_RIM_Z - (C.SEAM_LEDGE_Z + C.SEAM_LEDGE_CLEAR)
    gap = stack - to_ledge
    assert abs(gap - C.SEAM_LEDGE_CLEAR) < 1e-9, (
        f"ledge gap {gap:.3f} should reduce to SEAM_LEDGE_CLEAR {C.SEAM_LEDGE_CLEAR} — the Z "
        f"ladder and the seam have drifted apart"
    )
    assert gap >= 0.25, (
        f"seam ledge gap is only {gap:.3f} mm; a switch stack that runs {gap:.3f} mm shorter "
        f"than modelled would land the bottom's rim on the tub's ledge and hold the case open"
    )


def test_z_ladder_tracks_the_mx_gap():
    """Everything above the PCB is DERIVED from MX_BODY_CLEAR — nothing downstream may pin a
    literal. This is what makes re-measuring the switch stack a one-line change.

    Written as identities rather than expected numbers on purpose: a test that asserted
    'PLATE_SEAT_Z == 13.4' would have to be edited every time the measurement improves, and an
    edited test is one nobody re-derives. These hold at any MX_BODY_CLEAR.
    """
    assert C.PLATE_SEAT_Z == C.PCB_TOP_Z + C.MX_BODY_CLEAR
    assert C.PLATE_TOP_Z == C.PLATE_SEAT_Z + C.PLATE_THICKNESS
    assert C.MAIN_RIM_Z == C.PLATE_TOP_Z, "the rim must stay flush with the plate top"
    assert C.COVER_TOP_Z == C.MAIN_RIM_Z + C.COVER_THICKNESS
    # The slide pocket's cap is the one thing above the PCB that must NOT track the plate stack.
    # It used to be MAIN_RIM_Z − 0.5, which made its clearance an accident of the plate stack:
    # the rim answers to MX_BODY_CLEAR, and the switch can does not. Under that rule the cap
    # tracked to within 0.15 mm of the can at MX_BODY_CLEAR = 3.40, and went 0.9 mm negative
    # against a 5.0 mm can. It is now derived from the can and clamped by the lid, so these two
    # bounds are the whole contract and neither one moves when the plate stack does.
    assert C.SLIDE_ACTUATOR_TOP_Z >= (
        C.PCB_TOP_Z + C.SLIDE_ACTUATOR_BODY_H + C.SLIDE_ACTUATOR_CAP_CLEAR), (
        "slide pocket caps below the modelled can top + its clearance — the can cannot enter"
    )
    assert C.COVER_TOP_Z - C.SLIDE_ACTUATOR_TOP_Z >= C.SLIDE_ACTUATOR_LID_MIN, (
        "slide pocket eats into the lid — less than SLIDE_ACTUATOR_LID_MIN of cover survives"
    )


def test_the_switch_lever_is_reachable_through_the_window():
    """The finger window must expose the actuator lever over its whole height.

    This is the symptom that exposed the wrong ruler: on the printed part the lever's top sat
    level with the window's lower edge and the switch could not be worked. Both numbers were
    wrong at once — the lever was modelled 0.9 mm low and the rim 0.9 mm low — so the model
    showed a lever standing proud in a window while the hardware had it buried under the wall.
    """
    lever_lo = C.PCB_TOP_Z + C.SLIDE_ACTUATOR_NUB_BASE
    lever_hi = lever_lo + C.SLIDE_ACTUATOR_NUB_H
    assert C.SLIDE_SCOOP_FLOOR_Z < lever_lo, (
        f"window floor {C.SLIDE_SCOOP_FLOOR_Z} is at or above the lever underside {lever_lo} — "
        f"the lever is behind the wall"
    )
    assert lever_hi < C.MAIN_RIM_Z, (
        f"lever top {lever_hi} reaches the rim {C.MAIN_RIM_Z} — no material above it to hold "
        f"the window's upper edge"
    )
