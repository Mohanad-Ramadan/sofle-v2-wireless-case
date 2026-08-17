"""Rabbet snap latches in the real case parts.

The trap these guard against is a latch that *measures* fine and does nothing. Seated
interference between the halves is zero whether the barb sits correctly in its pocket OR
misses it entirely, so "0.000 mm^3" is necessary and nowhere near sufficient. The tests below
pin the barb and the pocket to the same place, check the arm is actually freed at both legs,
and check every cut that is supposed to be hidden really is.
"""
import math

import pytest
from build123d import Solid

from sofle_case import constants as C
from sofle_case.case import _seam_z_at, tent_ground_z
from sofle_case.snaps import (
    _corner_s_to_xy,
    _slot_v0,
    arm_wall_height,
    barb_center,
    barb_u,
    corner_barb_center,
    corner_cut_center,
    corner_strain,
    cut_center,
    cut_u,
    snap_report,
)
from tests.shared_builds import build_bottom_part, build_top_part

PROUD = C.SNAP_BARB_PROUD


def _to_case(arm, u, v):
    """Map a local (u, v) on an arm to case XY. +u is (out_y, -out_x); +v is outward."""
    ox, oy = arm.out
    return (arm.root[0] + oy * u + ox * v, arm.root[1] - ox * u + oy * v)


def _probe(part, x, y, z, d=0.5, dz=0.3):
    box = Solid.make_box(d, d, dz).translate((x - d / 2, y - d / 2, z - dz / 2))
    hit = part & box
    return 0.0 if hit is None else hit.volume


def _crest_z(arm):
    """Z of the barb's deepest point. At SNAP_RETURN_DEG = 90 the return face is flat, so the
    crest is the barb's own bottom — probe just above it, not at it, to stay off the face."""
    if C.SNAP_RETURN_DEG >= 90.0:
        return arm.barb_lo_z + 0.1
    return arm.barb_lo_z + PROUD / math.tan(math.radians(C.SNAP_RETURN_DEG))


@pytest.fixture(scope="module")
def bottom():
    return build_bottom_part("right")


@pytest.fixture(scope="module")
def top():
    return build_top_part("right")


def test_parts_remain_single_valid_solids(bottom, top):
    """Also the proof that every arm is attached at exactly one end: an arm severed at both
    ends would drop out of the bottom part as a second solid."""
    for name, part in (("bottom", bottom), ("top", top)):
        assert part.is_valid, f"{name} is not a valid solid"
        assert len(part.solids()) == 1, f"{name} is {len(part.solids())} solids"


def test_barb_crosses_the_gap_into_the_pocket(bottom):
    """The barb must protrude past the skirt's inboard line or it cannot engage anything. It
    stands proud SNAP_BARB_PROUD into a SEAM_FIT_CLEAR gap, so SNAP_DEFLECT of it lies inside
    the pocket."""
    for arm in C.SNAP_ARMS:
        z = _crest_z(arm)
        x, y = _to_case(arm, barb_u(arm), (C.SEAM_FIT_CLEAR + PROUD) / 2.0)
        assert _probe(bottom, x, y, z, d=0.3) > 1e-6, (
            f"{arm.name}: no barb material past the skirt line — missing or too shallow")
        x, y = _to_case(arm, barb_u(arm), PROUD + 0.15)
        assert _probe(bottom, x, y, z, d=0.3) < 1e-9, f"{arm.name}: barb overshoots its depth"


def test_catch_pocket_is_where_the_barb_is(top):
    """The load-bearing alignment check. At the barb's own location the TOP must be air, or the
    barb has nothing to drop into. A mislocated pocket still shows zero seated interference and
    the latch simply never clicks, which is why interference alone proves nothing."""
    for arm in C.SNAP_ARMS:
        x, y = _to_case(arm, barb_u(arm), (C.SEAM_FIT_CLEAR + PROUD) / 2.0)
        assert _probe(top, x, y, _crest_z(arm), d=0.3) < 1e-9, (
            f"{arm.name}: skirt material where the barb has to sit — pocket missing or "
            f"mislocated")


def test_skirt_survives_beyond_the_pocket_ends(top):
    """The pocket must be a bounded notch, not a channel that eats the whole skirt run."""
    reach = C.SNAP_BARB_X_LEN / 2 + 1.0 + 1.5      # half barb + pocket pad + margin
    for arm in C.SNAP_ARMS:
        for sign in (-1.0, +1.0):
            x, y = _to_case(arm, barb_u(arm) + sign * reach, C.SEAM_FIT_CLEAR + 0.4)
            assert _probe(top, x, y, _crest_z(arm), d=0.3) > 1e-6, (
                f"{arm.name}: skirt gone {reach} mm past the pocket end")


def test_arm_is_freed_on_both_legs(bottom):
    """Without the OUTBOARD leg the strip is built in at both ends, and fixed-fixed strain is
    12*d*h/L^2 against a cantilever's 3*d*h/(2L^2) — 2.84% at L=22, which fractures PLA."""
    for arm in C.SNAP_ARMS:
        z = C.SEAM_LEDGE_Z - 1.0
        # inboard leg, mid-arm
        x, y = _to_case(arm, arm.sense * arm.length / 2,
                        (_slot_v0(arm) - arm.thickness) / 2.0)
        assert _probe(bottom, x, y, z, d=0.3) < 1e-9, f"{arm.name}: inboard relief leg not cut"
        # outboard leg, through the rim at the free end
        x, y = _to_case(arm, cut_u(arm), -C.SEAM_RIM_THK / 2)
        assert _probe(bottom, x, y, z, d=0.3) < 1e-9, (
            f"{arm.name}: outboard leg not cut — the arm is fixed-fixed, not a cantilever")


def test_arm_root_stays_attached(bottom):
    """...or the 'fixed' end is not fixed."""
    for arm in C.SNAP_ARMS:
        x, y = _to_case(arm, -arm.sense * (C.SNAP_ROOT_FILLET + 1.5), -arm.thickness / 2)
        assert _probe(bottom, x, y, C.SEAM_LEDGE_Z - 1.0, d=0.3) > 1e-6, (
            f"{arm.name}: no material behind the root — the arm is not attached to anything")


def test_release_port_reaches_the_underside(bottom):
    """The slot runs to the wedge's ground face, which is what makes the strip a full-height
    cantilever. It doubles as a disassembly port, on a face nobody looks at."""
    for arm in C.SNAP_ARMS:
        x, y = _to_case(arm, arm.sense * arm.length / 2,
                        (_slot_v0(arm) - arm.thickness) / 2.0)
        g = tent_ground_z(y)
        assert _probe(bottom, x, y, g + 0.4, d=0.3) < 1e-9, (
            f"{arm.name}: relief slot does not reach the ground face")
        # probe-off-part sanity: the wedge beside the slot IS solid down there
        sx, sy = _to_case(arm, arm.sense * arm.length / 2, -arm.thickness / 2)
        assert _probe(bottom, sx, sy, g + 0.4, d=0.3) > 1e-6, (
            f"{arm.name}: the wedge beside the slot is missing too — probe is off the part")


def test_hidden_cuts_are_hidden_and_the_rest_are_declared(bottom, top):
    """THE test this whole design turns on.

    A cut severs the rim's outer face, and that face is bare wherever the reveal exposes it.
    For every arm flagged ``hidden_cut`` the tub's skin must stand outboard of the cut at every
    Z the cut spans. The five that are NOT flagged show a 1.2 mm slit in the reveal by
    decision — they are asserted to be exactly the five expected, so the exemption cannot
    quietly grow."""
    slit = {a.name for a in C.SNAP_ARMS if not a.hidden_cut} | {"N2-sw3-lobe"}
    assert slit == {"N1-canopy-N", "N2-sw3-lobe", "N3-north-east", "E2-east-N", "W2-west-N"}, (
        f"the set of arms showing a slit changed: {sorted(slit)}")

    for arm in C.SNAP_ARMS:
        if not arm.hidden_cut:
            continue
        _cx, cy = cut_center(arm)
        assert cy < C.TENT_SEAM_Y1, (
            f"{arm.name}: cut at y={cy:.2f} is north of TENT_SEAM_Y1={C.TENT_SEAM_Y1}, where "
            f"the reveal starts opening — measured zero-exposure runs to y=48.196, but the "
            f"margin between y1 and there depends on the wave's spline knots")
        # the skin must be outboard of the cut over the rim's whole covered height
        sx, sy = _to_case(arm, cut_u(arm), C.SEAM_FIT_CLEAR + C.SEAM_SKIN / 2)
        for z in (tent_ground_z(cy) + 0.6, C.SEAM_LEDGE_Z / 2, C.SEAM_LEDGE_Z - 0.8):
            assert _probe(top, sx, sy, z, d=0.3) > 1e-6, (
                f"{arm.name}: no tub skin covering its cut at Z={z:.2f} — the slot shows")


def test_every_barb_fits_its_hidden_band():
    """A barb needs SNAP_Z_BUDGET of band between the pocket's mouth chamfer and the rim's
    lead-in. The wave crests at SEAM_WAVE_CREST_Z and leaves less than that over part of the
    ramp — the BARB DEAD ZONE. Computed, never hard-coded: it moves when SNAP_Z_PLAY moves."""
    for arm in C.SNAP_ARMS:
        _bx, by = barb_center(arm)
        band = C.SNAP_BAND_CEIL - max(_seam_z_at(by), C.SNAP_BAND_FLOOR)
        assert band >= C.SNAP_Z_BUDGET, (
            f"{arm.name}: barb at y={by:.2f} has only {band:.3f} mm of hidden band against a "
            f"{C.SNAP_Z_BUDGET:.3f} mm budget — it is in the dead zone under the wave crest")


def test_seated_interference_is_zero(bottom, top):
    assert (bottom & top).volume < 1e-6


def test_closing_force_stays_hand_assemblable():
    """45 N is the ergonomic guideline for repeated assembly work, not a physical limit, and
    this case is closed occasionally by hand — so the guard is set at the point where a
    two-handed bench press stops being reasonable, not at the guideline."""
    total = sum(C.snap_force(a.thickness, arm_wall_height(a), a.length) for a in C.SNAP_ARMS)
    assert total <= 28.0, f"total deflection force {total:.1f} N; worst-case insertion would be "\
                          f"{C.snap_insertion_force(total, 0.7):.1f} N at mu=0.7"


def test_arms_clear_the_exclusion_zones():
    """The rubber-foot seats are what decide where arms can go — at FOOT_DIA 10 four of these
    nine fouled one. Checked against the slot's inboard edge and the root relief's own radius.

    THE GATE IS 1.2 mm, NOT 2.0, AND THAT IS MEASURED RATHER THAN CHOSEN. Sampling the whole
    slot line (not just its root/barb/cut, which is how an earlier survey got this wrong by
    3.5 mm) the tightest three are N3 at 1.35, E1 at 1.49 and E2 at 1.85. Nothing overlaps,
    and what is left between them is a web at the ground face 1.35 mm wide — three perimeters
    at a 0.4 mm nozzle — between a through-slot and a seat that is only FOOT_DEPTH (0.6 mm)
    deep. Widening it means moving the two x=143 feet inboard, and the last time a foot moved
    for the snaps the move did not survive. So the number is pinned here instead: if it drops
    below 1.2 something has shifted and the arms need re-surveying, not the guard relaxing."""
    holes = [C.pcb_to_case(hx, hy) for hx, hy in C.MOUNTING_HOLES]
    bx, by = C.pcb_to_case(*C.BATTERY_POCKET_POS)
    bhw = C.BATTERY_W / 2 + C.BATTERY_XY_CLEARANCE
    bhl = C.BATTERY_L / 2 + C.BATTERY_XY_CLEARANCE
    for arm in C.SNAP_ARMS:
        pts = [_to_case(arm, arm.sense * (arm.length + C.SNAP_TAB_SLOT_W) * k / 40.0,
                        _slot_v0(arm)) for k in range(41)]
        for fx, fy in C.FOOT_POSITIONS:
            gap = min(math.hypot(px - fx, py - fy) for px, py in pts) - C.FOOT_DIA / 2
            assert gap > 1.2, f"{arm.name}: slot is {gap:.2f} mm from foot ({fx},{fy})"
            rx, ry = _to_case(arm, 0.0, (_slot_v0(arm) - arm.thickness) / 2.0)
            rgap = math.hypot(rx - fx, ry - fy) - C.FOOT_DIA / 2 - C.SNAP_ROOT_FILLET
            assert rgap > 1.2, f"{arm.name}: root relief is {rgap:.2f} mm from foot ({fx},{fy})"
        for hx, hy in holes:
            gap = min(math.hypot(px - hx, py - hy) for px, py in pts) - C.STANDOFF_OD_LOWER / 2
            assert gap > 2.0, f"{arm.name}: slot is {gap:.2f} mm from standoff ({hx:.1f},{hy:.1f})"
        bat = min(max(bx - bhw - px, px - (bx + bhw), by - bhl - py, py - (by + bhl))
                  for px, py in pts)
        assert bat > 2.0, f"{arm.name}: slot is {bat:.2f} mm from the battery pocket"


def test_both_halves_get_the_latches():
    for side in ("left", "right"):
        part = build_bottom_part(side)
        assert part.is_valid and len(part.solids()) == 1, f"{side} bottom is not one solid"


def test_report_covers_every_arm():
    text = snap_report()
    for arm in C.SNAP_ARMS:
        assert arm.name in text, f"{arm.name} missing from snap_report()"
    assert "N2-sw3-lobe" in text, "the corner arm is missing from snap_report()"


# ---- N2, the arm that wraps the SW3 lobe's jog -----------------------------------------

def test_corner_arm_is_freed_and_attached(bottom):
    """It is built from a concentric BAND rather than local boxes, because a straight prism laid
    across the 4.24 mm arc floats off the wall and leaves disjoint solids. So the checks that
    matter are the same three as a straight arm — freed inboard, cut through at the free end,
    still attached at the root — asserted along the wrapped path rather than in a local frame."""
    z = C.SEAM_LEDGE_Z - 1.0
    rim_out = C.PCB_XY_CLEARANCE + C.SEAM_RIM_THK
    v_mid = (rim_out - C.SNAP_CORNER_THK) - C.SNAP_TAB_SLOT_W / 2   # centre of the slot band
    free_s = C.SNAP_CORNER_CUT_S + C.SNAP_TAB_SLOT_W
    lobe_s = C.SNAP_CORNER_LOBE[0][0] - C.SNAP_CORNER_LOBE[1][0]
    root_s = free_s + C.SNAP_CORNER_L
    # Sampled on BOTH runs so the band is proven to survive the arc, and the stations are
    # DERIVED from the same arc-length the builder uses — an earlier version guessed
    # "8 mm in from each run's start" and landed 1.04 mm past the root, where there is
    # correctly no slot at all, and read that as a missing relief.
    for s, where in (((free_s + lobe_s) / 2, "lobe"),
                     ((lobe_s + C.SNAP_CORNER_ARC + root_s) / 2, "west run")):
        x, y_rim = _corner_s_to_xy(s)
        assert _probe(bottom, x, y_rim - rim_out + v_mid, z, d=0.3) < 1e-9, (
            f"corner arm: inboard relief missing on the {where} at s={s:.2f}")
    # through-cut at the free end
    cx, cy = corner_cut_center()
    assert _probe(bottom, cx, cy - C.SEAM_RIM_THK / 2, z, d=0.3) < 1e-9, (
        "corner arm: outboard leg not cut — it is fixed-fixed, not a cantilever")
    # ...and material beyond it, or the arm is severed at both ends
    assert _probe(bottom, cx + 1.4, cy - C.SEAM_RIM_THK / 2, z, d=0.3) > 1e-6, (
        "corner arm: no rim beyond the free-end cut")


def test_corner_arm_barb_sits_over_sw3(bottom, top):
    """The lobe is the northernmost run on the case and SW3 (82.52, 111.29) is the switch behind
    it — placing the barb anywhere else on the lobe would hold the wrong thing."""
    bx, by = corner_barb_center()
    assert abs(bx - 82.52) <= C.SNAP_BARB_X_LEN / 2, (
        f"corner barb at x={bx:.2f} does not cover SW3 at x=82.52")
    z = C.SNAP_CORNER_BARB_LO_Z + 0.1
    assert _probe(bottom, bx, by + (C.SEAM_FIT_CLEAR + PROUD) / 2, z, d=0.3) > 1e-6, \
        "corner barb does not reach past the skirt line"
    assert _probe(top, bx, by + (C.SEAM_FIT_CLEAR + PROUD) / 2, z, d=0.3) < 1e-9, \
        "no catch pocket where the corner barb sits"


def test_corner_arm_beats_the_straight_alternative():
    """The reason this arm exists. The lobe alone is 18.00 mm, so a straight arm there is L=14
    and has to stay at h=1.20 to survive; wrapping past the arc buys 38.24 mm of rim to place a
    26 mm arm in at full-ish thickness. Guarded as a comparison, not a magic number, so that
    shortening the arm back to the lobe cannot pass silently."""
    straight = C.snap_strain(1.20, 14.0)
    assert corner_strain() < straight * 0.6, (
        f"the corner arm strains {corner_strain() * 100:.3f}% against a straight L=14 arm's "
        f"{straight * 100:.3f}% — it is no longer buying anything")
    assert corner_strain() <= min(C.snap_strain(a.thickness, a.length) for a in C.SNAP_ARMS)
