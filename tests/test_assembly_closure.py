"""Does the case actually SHUT over the keyboard?

Every other clearance test in this suite asks a local question — does this cutter clear that
body, is this pocket deep enough. The printed case failed three times anyway, because closure
is a global property and nothing asserted it:

  * the encoder plateau clipped the EC11 body            (fixed, 7a54949)
  * the cover windows bound on 29 switch collars         (fixed, d60d25d)
  * the plate rode on the switches, not the standoffs    (fixed, MX_BODY_CLEAR + PIN_RECESS)

Each one held the TOP off the switch plate on its own, and each one passed every test that
existed at the time. All three were found by printing the case, not by running the suite.

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
from build123d import Part, Plane, Pos, mirror

from sofle_case import constants as C
from sofle_case import knob as K
from sofle_case.pcb_phantom import (
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
        ("EC11 knob", _mirrored(K.place_knob(bottomed=True), side)),
    ]


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
