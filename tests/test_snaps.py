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
    corner_force,
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
        # The overshoot probe has to account for its own box being WORLD-axis-aligned: centred
        # at v it reaches v - (d/2)*(|nx| + |ny|) inboard, which is d/2 on an axis-aligned wall
        # but 1.22x that on the SE and SW diagonals. A flat PROUD + 0.15 therefore stood exactly
        # TANGENT to the crest on the straight walls — passing only because a knife edge
        # encloses no volume — and clipped the crest outright on the diagonals, reporting
        # 4.3e-05 mm^3 of "overshoot" from a barb that is exactly the depth it should be.
        # Stated as a real margin instead: nothing may reach 0.10 mm past the design crest.
        reach = (0.3 / 2.0) * (abs(arm.out[0]) + abs(arm.out[1]))
        x, y = _to_case(arm, barb_u(arm), PROUD + 0.10 + reach)
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
            # PROBE AT WHICHEVER IS HIGHER: the barb's own depth, or the wave's local lead-in
            # relief ceiling (seam_z(y) + SEAM_LEAD_IN) plus a little clearance. Near the crest
            # (W2, E2) the wave itself pushes the tub wall's own lower edge above the barb's
            # depth, so probing at the barb's Z alone finds nothing there NOT because the pocket
            # over-ran, but because ambient wall does not start that low at this Y any more --
            # a fixed Z stopped meaning "where the wall should be" once the wave grew tall enough
            # to matter here. Still inside the pocket's own band (SNAP_Z_PLAY below barb_lo_z to
            # SNAP_BARB_H above it) for every arm, so an over-wide pocket still gets caught.
            z = max(_crest_z(arm), _seam_z_at(y) + C.SEAM_LEAD_IN + 0.1)
            assert _probe(top, x, y, z, d=0.3) > 1e-6, (
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
    Z the cut spans. The rest show a 1.2 mm slit in the reveal by decision — they are asserted
    to be exactly the set expected, so the exemption cannot quietly grow.

    That set grew from five to seven when the whole rim was evenly spaced. E1 and W1 used to
    cut under the skin at y=39.60; even spacing carries their barbs north to y=53.50 and 55.71,
    and a cut sits 5.0 mm beyond its own barb, so neither can reach back under the line in
    either sense. Losing two hidden cuts is the price of even retention, taken deliberately."""
    slit = {a.name for a in C.SNAP_ARMS if not a.hidden_cut} | {"N2-sw3-lobe"}
    assert slit == {"E1-east-S", "N1-canopy-N", "N2-sw3-lobe", "N3-north-east", "E2-east-N",
                    "W1-west-S", "W2-west-N"}, (
        f"the set of arms showing a slit changed: {sorted(slit)}")

    for arm in C.SNAP_ARMS:
        if not arm.hidden_cut:
            continue
        _cx, cy = cut_center(arm)
        assert cy < C.TENT_SEAM_Y1, (
            f"{arm.name}: cut at y={cy:.2f} is north of TENT_SEAM_Y1={C.TENT_SEAM_Y1}, where "
            f"the reveal starts opening — measured zero-exposure runs to y=54.87, but the "
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
    """SCREWLESS design: the snaps are the sole closure. AGGRESSIVE-HOLD retune (2026-08-26)
    deliberately raised closing force for a firmer seat and louder click: thicker arms (2.35 mm long
    arms) x deeper deflect (0.40) put the deflection total at ~69 N, insertion ~78 N at mu=0.5 and
    ~106 N at mu=0.7. That is a firm, two-handed close by design — NOT a light one-hand snap.

    The HOLD still comes from the 90 deg self-locking undercut, not deflection force, so this gate
    is NOT a hold check — it is the runaway-insertion guard: it stops a future edit from pushing
    closing force past what two hands can seat (the 2.55 mm / deflect 0.42 experiment hit ~160 N and
    was rejected as un-closeable for zero retention gain). Ceiling set at 72 N deflection (~110 N at
    mu=0.7) — just above the intended ~69 N, so any further creep trips it and forces a re-decision.

    The sum includes corner_force() — it once omitted the N2 corner entirely, a real gap that
    hid 2.57-3.91 N of the true total from every historical closing-force check."""
    total = (sum(C.snap_force(a.thickness, arm_wall_height(a), a.length) for a in C.SNAP_ARMS)
             + corner_force())
    assert total <= 72.0, f"total deflection force {total:.1f} N; worst-case insertion would be "\
                          f"{C.snap_insertion_force(total, 0.7):.1f} N at mu=0.7"


def test_fatigue_strain_has_margin_for_a_screwless_shell():
    """SCREWLESS binds on CYCLIC FATIGUE, not force: the snaps flex every time the (rare-open)
    shell is opened, and PLA fatigues near its strain limit. The AGGRESSIVE-HOLD retune (2026-08-26)
    deliberately spent some of the old fatigue margin — deflect 0.25 -> 0.40 — for a firmer seat and
    louder click, and raised the PLA cap 0.005 -> 0.006 to match. T1-thumb-gulf is the bottleneck
    (L=13 pinned by GULF_A, h at the 1.5 mm print floor); its strain is SNAP_DEFLECT alone and now
    sits 0.533 % (89 % of the 0.6 % cap). SW1 is the next bottleneck at 0.469 %, every other arm
    <= 0.35 %. Gate at 0.55 % — it holds
    the worst arm just under the cap with a thin, intentional margin; going higher needs a real
    re-decision (a frequently-opened shell should walk deflect back toward the old 0.005 margin)."""
    strains = [C.snap_strain(a.thickness, a.length) for a in C.SNAP_ARMS] + [corner_strain()]
    worst = max(strains)
    assert worst <= 0.0055, f"worst root strain {worst*100:.3f}% exceeds the 0.55% fatigue-margin gate"


def test_undercut_overlap_retains():
    """Retention is the 90 deg undercut's job. The barb-into-catch overlap is SNAP_DEFLECT
    (proud minus the seam fit clearance); it must stay positive with sane margin so the barb
    actually hooks. Fracture-limited, not overlap-limited, so a small overlap still holds — but
    it must not go to zero when proud is tuned down for strain."""
    assert C.SNAP_DEFLECT >= 0.20, f"undercut overlap {C.SNAP_DEFLECT:.3f} mm too small to retain"


def test_arms_clear_the_exclusion_zones():
    """Foot seats against snap arms, checked on the slot's inboard edge and the root relief's
    own radius.

    THE GATE IS 1.2 mm, NOT 2.0, AND THAT IS MEASURED RATHER THAN CHOSEN. What it protects is
    a web at the ground face between a through-slot and a seat only FOOT_DEPTH (0.6 mm) deep;
    1.2 mm is three perimeters at a 0.4 mm nozzle. Sample the WHOLE slot line, not just its
    root/barb/cut — that shortcut is how an earlier survey got this wrong by 3.5 mm.

    THE SEATS NO LONGER DECIDE WHERE THE ARMS GO, WHICH IS A REVERSAL WORTH SPELLING OUT. This
    used to read "at FOOT_DIA 10 four of these nine fouled one", and the fix taken then was to
    shrink the seats to Ø8 — on the reasoning that moving a foot had been tried on
    wip/snap-latches and had not survived. Both halves of that lapsed underneath this test: the
    arms went to ELEVEN on even arc-length stations and every slot the Ø10 survey had measured
    moved. Re-measured on the layout that ships, Ø10 fouls nothing; it only grazed the
    printability gate, and three feet moving 1.6-1.9 mm INBOARD bought that back with room to
    spare. Tightest now, at SNAP_TAB_SLOT_W = 1.2: E2 at 1.86, W2 at 2.04, N3 at 2.05 (that last
    on its root relief rather than its slot line) — every one of them beyond the Ø8 layout's own
    tightest (1.76 at SE1). Widening the slot back 0.9 -> 1.2 for printability spent up to
    0.30 mm of each of those and the feet still did not have to move; the gate is what says so.

    So if this drops below 1.2 again, re-survey the arms AND re-check whether a foot can move
    before touching FOOT_DIA. Shrinking the seat is what a user notices; it is the one number
    here that has to match hardware they already own."""
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


_RIM_ARC_CACHE: dict[str, tuple[list[tuple[float, float, float]], float]] = {}


def _rim_arc_length_of(xy):
    """Arc-length position of a point on the plate rim's outline, plus the outline's length.

    Discretised rather than solved in closed form: the outline is 25 edges of mixed line and
    arc, and all this has to settle is WHICH RUN a barb sits on and how far along it — a
    resolution of a few hundredths is far finer than any regression worth catching."""
    if "rim" not in _RIM_ARC_CACHE:
        from build123d import Plane

        from sofle_case.tray import offset_extruded
        part = offset_extruded(C.PCB_XY_CLEARANCE + C.SEAM_RIM_THK, 0.0, C.SEAM_LEDGE_Z)
        face = min(part.faces().filter_by(Plane.XY), key=lambda f: f.center().Z)
        wire = face.outer_wire()
        n = 6000
        pts = [((wire @ (i / n)).X, (wire @ (i / n)).Y, i / n * wire.length)
               for i in range(n + 1)]
        _RIM_ARC_CACHE["rim"] = (pts, wire.length)
    pts, length = _RIM_ARC_CACHE["rim"]
    x, y = xy
    return min(pts, key=lambda p: (p[0] - x) ** 2 + (p[1] - y) ** 2)[2], length


def test_every_barb_is_evenly_spaced_around_the_whole_rim():
    """THE reason the arms sit where they do — and the thing a well-meaning nudge is most likely
    to undo, because nothing else in the suite would notice.

    All ELEVEN barbs (the ten straight arms plus N2 on the lobe) divide the 495.26 mm outline
    into steps of 43.75-46.37 mm against an ideal of 45.02. An earlier layout evened out only
    the southern stretch and left the rest alone, which ran 32.32 to 56.95.

    Eleven is not a free choice. Only about half the rim can carry a barb at all — corner arcs
    are unbuildable, the north runs are too short, and the dead zone rules out part of both side
    walls — so the best achievable max gap is 58.33 mm at nine arms, 55.28 at ten, 45.63 at
    eleven and 45.58 at twelve. Deleting an arm to "thin out" a crowded-looking wall makes the
    case worse, and the arm the spacing maths would drop is an EAST one, not a southern one.

    Asserted as the SPREAD between gaps rather than against hard-coded stations, so the whole
    ring may slide when the outline changes — it just may not go back to clustering.

    THE NE CORNER IS A NAMED EXCEPTION, NOT A LOOSENED THRESHOLD. E2-east-N sits at its rim run's
    physical ceiling (see the note above SNAP_ARMS) because a snap that feels wrong under a
    printer's nozzle was judged worse than an uneven rim there — a deliberate reversal of this
    test's usual priority, scoped to exactly the four gaps that touch E1-east-S, E2-east-N and
    N3-north-east. The other eight arms are re-solved around that fixed point and held to the
    same strict spread as before (in fact tighter, 2.39 mm); only the NE corner's own four gaps
    are exempted from it, and even those stay inside a generous sanity bound so a real regression
    (an arm silently landing on top of another, say) still fails loudly."""
    arms = {a.name: a for a in C.SNAP_ARMS}
    assert len(arms) == 10, f"expected 10 straight arms, found {len(arms)}"

    NE_CORNER = {"E1-east-S", "E2-east-N", "N3-north-east"}
    centres = [(a.name, barb_center(a)) for a in C.SNAP_ARMS] + [("N2-sw3-lobe", corner_barb_center())]
    tagged, length = [], 0.0
    for name, c in centres:
        s, length = _rim_arc_length_of(c)
        tagged.append((s, name))
    tagged.sort()
    n = len(tagged)
    gaps = [(tagged[(i + 1) % n][0] - tagged[i][0]) % length for i in range(n)]
    named_gaps = [(gaps[i], tagged[i][1], tagged[(i + 1) % n][1]) for i in range(n)]

    corner_gaps = [g for g, a, b in named_gaps if a in NE_CORNER or b in NE_CORNER]
    other_gaps = [g for g, a, b in named_gaps if a not in NE_CORNER and b not in NE_CORNER]
    assert len(corner_gaps) == 4, f"expected 4 gaps touching the NE corner, found {len(corner_gaps)}"

    ideal = length / n
    assert max(other_gaps) - min(other_gaps) < 4.0, (
        "the eight arms outside the NE corner are no longer evenly spaced: gaps "
        + ", ".join(f"{g:.2f}" for g in sorted(other_gaps))
        + f" (spread {max(other_gaps) - min(other_gaps):.2f}, ideal step {ideal:.2f})")
    assert max(other_gaps) < 48.0, (
        f"widest unlatched stretch outside the NE corner is {max(other_gaps):.2f} mm; "
        f"should be under 48")
    # Generous, not strict: the NE corner is the accepted exception, but a gap collapsing near
    # zero (arms overlapping) or ballooning past a sane multiple of the ideal step is still a
    # real regression, not the trade-off this test now accepts.
    assert all(15.0 < g < 60.0 for g in corner_gaps), (
        f"NE corner gap out of sane bounds: {sorted(corner_gaps)}")
    assert sum(gaps) == pytest.approx(length, abs=1e-6)


def test_every_barb_sits_at_one_height():
    """The barbs share a single ``barb_lo_z``, and that is a CORRECTION, not a simplification.

    They used to climb a 0.30 mm ladder from 1.40 to 4.40, on the grounds that a shared datum
    would make all eleven peak in the same instant and that staggering would break "a single
    60 N wall into eleven small ones". Simulating the closure — the barb's own profile against
    the skirt's inner face, with the catch pocket riding up with the tub — puts the peak at
    100% of the total either way: about 1.15 mm above seated every pocket has cleared its own
    barb, and past that point every arm bears on solid skirt at once whatever height it sits at.
    There is no instant to stagger. The claim was asserted in a comment and never measured.

    What the ladder did change is the skirt left above each catch pocket, which ran 1.30 mm at
    the top rung against 4.30 mm at the bottom. The thin end is where the skirt would split, so
    one height is strictly better, and this test is what keeps it that way."""
    zs = {a.barb_lo_z for a in C.SNAP_ARMS} | {C.SNAP_CORNER_BARB_LO_Z}
    assert len(zs) == 1, f"barb heights have drifted apart again: {sorted(zs)}"
    z = zs.pop()

    skirt = (C.SEAM_LEDGE_Z + C.SEAM_LEDGE_CLEAR) - (z + C.SNAP_BARB_H)
    assert skirt >= C.SNAP_SKIRT_ABOVE_MIN, (
        f"only {skirt:.3f} mm of skirt survives above every pocket, under "
        f"SNAP_SKIRT_ABOVE_MIN={C.SNAP_SKIRT_ABOVE_MIN}")

    # No barb may sit in a dead zone — where the wave-lifted seam floor plus the skirt kept below
    # the pocket rises past barb_lo_z and eats that skirt. This used to be asserted INDIRECTLY, by
    # claiming the per-arm BAND check (SNAP_BAND_CEIL - SNAP_Z_BUDGET) is always the tighter of two
    # exclusions so it alone suffices. That was a coincidence of the barb height: the screwless
    # re-tune shortened the barb (proud 0.52 -> 0.45 => SNAP_BARB_H 0.90 -> 0.78, SNAP_Z_BUDGET
    # 2.15 -> 2.03), and the two exclusions crossed (band 3.671 vs barb-height 3.650). So assert
    # the PHYSICAL fact directly, per arm at its own barb y — robust to the barb height either way.
    all_barbs = ([(a.name, barb_center(a)[1], a.barb_lo_z) for a in C.SNAP_ARMS]
                 + [("N2-sw3-lobe", corner_barb_center()[1], C.SNAP_CORNER_BARB_LO_Z)])
    for name, by, blo in all_barbs:
        skirt_below = blo - (_seam_z_at(by) + C.SNAP_SKIRT_BELOW)
        assert skirt_below >= 0.0, (
            f"{name}: barb at z {blo:.2f} sits in a dead zone — seam floor {_seam_z_at(by):.2f} + "
            f"SNAP_SKIRT_BELOW {C.SNAP_SKIRT_BELOW} leaves {skirt_below:.3f} mm of skirt below it")
    assert z + C.SNAP_BARB_H <= C.SNAP_BAND_CEIL, "the barb now runs into the rim's lead-in"


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
