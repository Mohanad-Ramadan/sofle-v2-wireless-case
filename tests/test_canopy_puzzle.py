"""Tests for the canopy roofs' PUZZLE strokes — two CURVES that each cross BOTH halves.

The design's whole claim is that the four strokes are really two curves seen in two splayed frames,
so the mark completes only when both halves are on the desk. Each mark is its fitted line plus an
odd-cubic lateral profile about the seam, ``PUZZLE_CURVE_A`` mm at the span's end: the bend is spent
out on the roofs and the hand-over across the gap stays flat. These tests pin that claim and the
things that could quietly break it:

  1. ONE CURVE in the assembled frame. Every vertex of both halves lies on ONE polyline to numerical
     zero (~1e-14 mm) — the curved version of the exact collinearity the straight marks had, and it
     must stay exact for the same reason: the halves sample one shared parameter grid rather than
     being aimed at each other. If it ever becomes merely small, someone has replaced the derivation
     with transcription.
  1b. That polyline IS the analytic cubic, to within ``PUZZLE_CHORD_SAG`` (measured 0.012 mm). A
     separate claim with its own number: (1) says the two halves cut one polyline, this says the
     polyline is the curve.
  2. The two halves must NOT match. That is a consequence of the design, not a decoration: one curve
     meets each canopy at a different angle. If the halves ever agree, the splay has gone to zero and
     the idea has collapsed.
  3. A stroke CROSSES THE RAMP, which is why the cutter clips against a NORMAL-offset roofline
     instead of measuring depth vertically. A test pins that one still does, so the construction
     cannot be "simplified" to a vertical drop without a failure. What it may spend there is a FIELD,
     not a constant (`canopy.puzzle_depth_at`): the shell measured perpendicular thins by cos θ on
     the ramp, and the depth dies to exactly zero at the ramp foot, where the roof becomes the
     cover's own 1.0 mm membrane.
  3b. Where each stroke STOPS was measured from the sketch too (`PUZZLE_STROKE_COVER`), not chosen.
     The trims are no longer CUT — the approved curve needs the full runs — but they still shape the
     mark, because `PUZZLE_CURVE_SPAN` is derived from the straight layout that includes them.
  4. Terminals. Every stroke runs out to the roof's own edge on the gap side (the west chamfer's top
     line, or the north one for the stroke aimed too far north to reach it) so the continuation
     across the gap reads. The east arris is broken ONCE IN THE PAIR — on the right half — not once
     per half: at A = 4.75 the bow lifts the left half's upper mark off that wall, a loss taken
     deliberately when the amplitude was chosen. Ends are square, never rounded.

Depth is asserted NORMAL to the surface, never vertically: the right half's ramp tips to 35.9°, where
a vertical measurement of a 0.5 mm groove reads 0.62 mm.
"""
import math

import pytest
from build123d import Solid, GeomType
from OCP.BRepCheck import BRepCheck_Analyzer

from sofle_case import constants as C
from sofle_case import canopy as CAN
from sofle_case import canopy_puzzle as PZ
from tests.shared_builds import build_canopy
from tests.shared_builds import build_top_part

SIDES = ["right", "left"]


def _roof_top(part, x, y, s=0.08):
    col = Solid.make_box(s, s, 40).translate((x - s / 2, y - s / 2, 0))
    inter = part & col
    solids = [] if inter is None else list(inter.solids())
    return max(ss.bounding_box().max.Z for ss in solids) if solids else None


def _solid_at(part, x, y, z, s=0.3):
    box = Solid.make_box(s, s, s).translate((x - s / 2, y - s / 2, z - s / 2))
    inter = part & box
    return inter is not None and sum(ss.volume for ss in inter.solids()) > 1e-6


def _walk(seg, t):
    """The point a fraction ``t`` of the way ALONG a stroke, measured by arclength."""
    steps = [math.dist(a, b) for a, b in zip(seg, seg[1:])]
    want = sum(steps) * t
    for (a, b), d in zip(zip(seg, seg[1:]), steps):
        if want <= d or (a, b) == (seg[-2], seg[-1]):
            f = 0.0 if d < 1e-12 else min(1.0, want / d)
            return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
        want -= d
    return seg[-1]


def _y_at_x(seg, x):
    """Where a stroke crosses the vertical line ``x``, or None. The first crossing, walking the
    polyline from its south end — a bowed mark can cross the same X twice, and every caller here
    wants the run-out, which is the first one."""
    for a, b in zip(seg, seg[1:]):
        if min(a[0], b[0]) <= x <= max(a[0], b[0]) and abs(b[0] - a[0]) > 1e-12:
            return a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0])
    return None


def _stations(side, seg, n, lo=0.05, hi=0.95):
    """``n`` sample points spaced by ARCLENGTH along a stroke, dropping the ones off the flat roof.

    Along the polyline, never between its ends: the marks are curves, and a stroke's chord leaves the
    groove by up to PUZZLE_CURVE_A — 4.75 mm at mid-span, which is open roof. Every probe would then
    read "no material removed" and the depth tests would fail for a reason that has nothing to do
    with the cut.

    Every stroke runs OUT of the roof at one end or both, so its extreme stations are either in open
    air (past the east wall / the north wall) or on the west shoulder facet, where the surface has
    already fallen away below the cutter. A probe there measures nothing and would read as a missing
    groove. Bounded by the geometry rather than by a fixed t, so the surviving stations still reach
    right up to each break."""
    x_w = CAN.CANOPY_WEST_OUTER_X + CAN.canopy_top_chamfer(side)[1] + 0.3   # past the facet arris
    out = []
    for k in range(n):
        x, y = _walk(seg, lo + (hi - lo) * k / (n - 1))
        if x_w < x < CAN.CANOPY_EAST_X - 0.3 and y < CAN.CANOPY_NORTH_OUTER_Y - 1.5:
            out.append((x, y))
    assert len(out) >= n // 3, "the roof clip ate most of the stations — check the stroke's ends"
    return out


def _normal_depth(part, x, y, z_ridge):
    t = _roof_top(part, x, y)
    if t is None:
        return None
    m = CAN._roofline_slope(y, z_ridge)
    return (CAN._canopy_roof_z(y, z_ridge) - t) / math.sqrt(1 + m * m)


@pytest.fixture(scope="module")
def bare():
    return {s: build_canopy(side=s, puzzle=False) for s in SIDES}


@pytest.fixture(scope="module")
def cut():
    return {s: build_canopy(side=s) for s in SIDES}


@pytest.fixture(scope="module")
def segs():
    return {s: CAN.canopy_puzzle_strokes(s) for s in SIDES}


# --------------------------------------------------------------------------------------------
# the idea itself
# --------------------------------------------------------------------------------------------

def test_the_two_halves_strokes_lie_on_one_curve_when_assembled(segs):
    """THE test for this feature. Every vertex of both halves — not just the ends — must lie on ONE
    assembled polyline to numerical zero, because they are pieces OF that polyline: both halves are
    sampled from the same t grid and then clipped. Anything above ~1e-9 means the derivation has been
    replaced by transcription somewhere.

    This is the curved successor to exact collinearity and it is the same statement, which is the
    point: bending the mark cost nothing in the property the whole design rests on. Measured today:
    3.2e-14 and 2.1e-14 mm."""
    spread = PZ.assembled_offcurve_spread(segs)
    for i, s in enumerate(spread):
        assert s < 1e-9, f"line {i}: a vertex sits {s:.3e} mm off the single assembled curve"


def test_the_sampled_polyline_really_is_the_curve():
    """The other half of the continuity story. ``assembled_offcurve_spread`` says the two halves cut
    one polyline; this says that polyline is the analytic cubic and not a coarse impression of it.

    Budgeted rather than tightened for its own sake: the step is derived from the curve's own
    tightest radius (``chord = √(8·R·sag)``), so refining ``PUZZLE_CHORD_SAG`` adds planar faces
    linearly. It is NOT ``CANOPY_RAMP_SAMPLES``, which densifies a spline and has a documented cliff.
    Measured: 0.012 mm on both lines, a sixteenth of a 0.2 mm layer."""
    for i in range(len(PZ.PUZZLE_LINES)):
        sag = PZ.polyline_sag(i)
        assert sag <= PZ.PUZZLE_CHORD_SAG, \
            f"line {i}: the sampled polyline departs {sag:.4f} mm from the cubic"


def test_the_curve_stays_a_drawn_line_not_a_hook():
    """A 1.0 mm groove that turns too tightly stops reading as a drawn stroke. Pinned against
    ``PUZZLE_CURVE_MIN_R`` (25 mm), and separately against the amplitude that was actually approved:
    at A = 7 the radii are 38.6 and 39.3 mm (was 46.8 / 47.7 at 4.75), so there is ~1.5× of
    headroom before the shape itself is in question — and ~75× against the width, which is the
    fold-over limit ``_band_offsets`` guards."""
    for i in range(len(PZ.PUZZLE_LINES)):
        r = PZ.curve_min_radius(i)
        assert r >= PZ.PUZZLE_CURVE_MIN_R, f"line {i} bends to R={r:.1f} mm"
        assert r >= 35.0, f"line {i}: R={r:.1f} mm — the approved mark at A=7 measured 38.6 / 39.3"


def test_the_parameterisation_still_comes_from_the_shipped_straight_layout(segs):
    """``PUZZLE_CURVE_SPAN`` is the one input that decides what the amplitude MEANS, so it is pinned
    AND re-derived — a pinned number nobody re-derives is a number that has quietly become a fiction.

    Derived from anything else the mark changes shape: from the raw safe-region chords, line A's span
    comes out 89.5 mm with the seam at u 0.72, and the same A = 4.75 then produces a lateral departure
    of 0.4 mm, i.e. a mark that is visually straight. It also must NOT follow the curve's own
    allowances — the ramp-foot bound and the dropped trims — or re-tuning an allowance would silently
    redraw the mark."""
    straight = {s: CAN.straight_puzzle_strokes(s) for s in SIDES}
    for i in range(len(PZ.PUZZLE_LINES)):
        got = PZ.span_from_straight(i, straight)
        for a, b, what in zip(got, PZ.PUZZLE_CURVE_SPAN[i], ("t_lo", "t_hi", "u_seam")):
            assert abs(a - b) < 1e-6, f"line {i}: {what} is {a:.6f}, pinned as {b:.6f}"
    assert PZ.PUZZLE_STROKE_COVER, \
        "the sketch's trims are gone — the span they helped define is no longer derivable"


def test_switching_the_curve_off_gives_back_the_straight_mark():
    """``PUZZLE_CURVE_A = 0`` is not "nearly straight", it IS the straight layout: the profile is
    identically zero, ``_drop_collinear`` collapses the sampling back to two points per stroke, and
    the strokes land on the fitted lines to 1.4e-14 mm. That is what makes the amplitude a dial with
    a meaningful zero rather than a rewrite.

    The two TRIMMED strokes are the exception and the exception is the point: they come back at full
    length, because the trims are no longer cut. Everything else about them is unchanged."""
    saved = PZ.PUZZLE_CURVE_A
    try:
        PZ.PUZZLE_CURVE_A = 0.0
        flat = {s: CAN.canopy_puzzle_strokes(s) for s in SIDES}
    finally:
        PZ.PUZZLE_CURVE_A = saved
    straight = {s: CAN.straight_puzzle_strokes(s) for s in SIDES}
    for side in SIDES:
        for i in range(len(PZ.PUZZLE_LINES)):
            assert len(flat[side][i]) == 2, \
                f"{side} line {i}: a zero-amplitude mark came back as {len(flat[side][i])} points"
            if (side, i) in PZ.PUZZLE_STROKE_COVER:
                continue                      # trimmed in the straight layout, not in what is cut
            for a, b in zip(flat[side][i], straight[side][i]):
                assert math.dist(a, b) < 1e-9, f"{side} line {i}: {a} is not the straight {b}"


def test_redesigning_at_a_different_separation_stays_exact(segs):
    """DESIGN-time: the separation is an input that decides where the curves cross each roof. Changing
    it must re-place the strokes and keep them on ONE curve exactly — that is what makes the layout a
    derived quantity rather than four tuned numbers.

    Note what does NOT move with it: ``PUZZLE_CURVE_SPAN``, which stays pinned to the fitted layout.
    That is deliberate — the separation decides which piece of the mark lands on each roof, not what
    the mark is — and it is why re-placing the halves cannot quietly change the amplitude's meaning.

    The usable design window is about +8 mm; past ~12 mm line 0 slides off the right roof entirely,
    at which point ``strokes`` raises rather than silently emitting nothing."""
    saved = PZ.PUZZLE_RIGHT_OFFSET
    try:
        for d in (-6.0, 4.0, 8.0):
            PZ.PUZZLE_RIGHT_OFFSET = (saved[0] + d, saved[1])
            moved = {s: CAN.canopy_puzzle_strokes(s) for s in SIDES}
            assert moved["right"] != segs["right"], f"{d:+} mm should re-place the strokes"
            for i, s in enumerate(PZ.assembled_offcurve_spread(moved)):
                assert s < 1e-9, f"line {i} left the single curve at {d:+} mm ({s:.2e} mm)"
    finally:
        PZ.PUZZLE_RIGHT_OFFSET = saved


def test_one_line_is_placement_tolerant_and_the_other_is_not():
    """USE-time, and the honest limit of the whole idea: the grooves are fixed once printed, so if the
    halves are then placed at a different separation than designed, each line breaks by the component
    of that error PERPENDICULAR to itself.

    A near-level line barely notices (its direction is nearly the error's direction); a steep one
    notices almost fully. Measured here so the number is on record rather than assumed:
      line 0, 53.9° from horizontal → 0.81 mm of break per mm of misplacement
      line 1,  2.5° from horizontal → 0.04 mm per mm
    With the 1.0 mm groove, line 0 still reads as joined for about ±0.6 mm of misplacement and line 1
    for about ±11 mm. Keeping ONE forgiving line in the pair is deliberate: the design degrades by
    half rather than all at once.

    THE BASELINE'S ARITHMETIC IS STILL EXACTLY RIGHT, even though the marks are curved, and that is a
    property of where the bend was put rather than an approximation: the profile is an odd cubic
    about the SEAM, so at the seam it is zero, flat AND has zero curvature. The two halves therefore
    hand over along the baseline's own direction, and a misplaced pair breaks by the same perpendicular
    component it always did — no kink on top of the step. Bending the mark anywhere else would have
    made this test a lie."""
    sens = []
    for ang, _off in PZ.PUZZLE_LINES:
        th = math.radians(ang)
        sens.append(abs(math.cos(th)))          # |n·x̂| = break per mm of X misplacement
    assert min(sens) < 0.15, \
        f"no placement-tolerant line left in the pair (sensitivities {[round(s, 3) for s in sens]})"
    assert max(sens) > 0.5, \
        "both lines are near-level now; the pair has lost its diagonal"
    half_w = CAN.CANOPY_PUZZLE_W / 2
    tol = [half_w / s for s in sens]
    assert max(tol) > 10.0, f"even the forgiving line only tolerates {max(tol):.1f} mm"
    # ...and the seam really is where the profile vanishes, which is what licenses the line
    # arithmetic above. Checked on the curve itself rather than trusted from the formula.
    for i in range(len(PZ.PUZZLE_LINES)):
        t_lo, t_hi, u_seam = PZ.PUZZLE_CURVE_SPAN[i]
        t_seam = t_lo + (t_hi - t_lo) * u_seam
        e = (t_hi - t_lo) * 1e-4
        d0, d1, d2 = (PZ.curve_lateral(i, t_seam + k * e) for k in (-1, 0, 1))
        assert abs(d1) < 1e-9, f"line {i}: the mark is {d1:.3e} mm off its baseline AT the seam"
        assert abs(d2 - 2 * d1 + d0) / (e * e) < 1e-6, \
            f"line {i}: the profile is curved at the seam — the halves hand over with a kink"


def test_the_halves_are_not_alike(segs):
    """A consequence of the splay, not a styling choice — so assert it as a consequence.

    Measured on the stroke's whole CHORD, first vertex to last. The old version read ``seg[1]``,
    which on a polyline is the second sample rather than the far end: it measured the first 1.5 mm of
    a 27 mm mark and would have gone on passing while the halves converged everywhere else.

    Today, dx/dy of the chords: line 0 is +1.417 on the left against +0.083 on the right; line 1 is
    −2.617 against −1.548."""
    assert segs["left"] != segs["right"]
    for i in range(len(PZ.PUZZLE_LINES)):
        def slope(side, i=i):
            a, b = segs[side][i][0], segs[side][i][-1]
            return (b[0] - a[0]) / (b[1] - a[1])
        dl, dr = slope("left"), slope("right")
        assert abs(dl - dr) > 0.5, \
            f"line {i}: the halves meet it at nearly the same angle ({dl:+.3f} vs {dr:+.3f}) — " \
            f"the splay has collapsed and the halves now look alike"


def test_canopy_line_and_assembled_line_agree():
    """``line_in_canopy`` and ``to_assembled`` are two views of one BASELINE; a point satisfying the
    canopy-frame equation must land on the assembled-frame line. If these ever disagree the strokes
    would still be drawn, just not where the design says.

    Checked on the baseline itself now, not on the strokes: the strokes are curves and no longer
    satisfy either equation — that is what the curve IS. The baseline is still the thing both frames
    have to agree about, because the profile is added along its normal in the assembled frame and
    pulled back through ``to_canopy``.

    Uses ``line_offset``, the AS-BUILT offset, not the raw fitted one — a nudge that reached one view
    of the line but not the other would desynchronise the halves, and reading the fitted value here
    would hide exactly that."""
    for side in SIDES:
        for i in range(len(PZ.PUZZLE_LINES)):
            ang, off = PZ.PUZZLE_LINES[i][0], PZ.line_offset(i)
            a, b, c = PZ.line_in_canopy(side, i)
            th = math.radians(ang)
            n = (math.cos(th), -math.sin(th))
            for y in (60.0, 90.0, 120.0):
                p = ((c - b * y) / a, y)
                q = PZ.to_assembled(p, side)
                assert abs(n[0] * q[0] + n[1] * q[1] - off) < 1e-9, \
                    f"{side} line {i}: the canopy-frame line misses the assembled one at y={y}"


def test_the_frames_are_exact_inverses():
    """``to_canopy`` is new plumbing and it is load-bearing: the mark is drawn ONCE in the assembled
    frame and pulled back into each half to be cut, so an inexact inverse would not fail loudly — it
    would shift one half's piece of the mark by whatever the error is, and the continuity test would
    still pass, because both halves would be shifted through the same broken map.

    So pin it directly, in both directions. Measured: 3.2e-14 mm."""
    for side in SIDES:
        for p in ((10.0, 60.0), (20.0, 90.0), (30.0, 120.0), (35.6, 108.5)):
            back = PZ.to_canopy(PZ.to_assembled(p, side), side)
            assert math.dist(p, back) < 1e-9, f"{side}: {p} → {back} is not a round trip"


def test_a_stroke_still_crosses_the_ramp(segs):
    """Which is why the cutter clips against a NORMAL-offset roofline. If this ever drops to ZERO,
    the vertical-depth shortcut starts looking safe — and it is not, because on the 35.9° ramp it
    thins a 0.5 mm groove to 0.40, i.e. it would go shallow exactly where the surface is most
    visible while still passing any "did it cut?" check.

    Two do, since the trims stopped being cut: the left half's line 1 and the right half's line 0,
    the latter running the ramp's whole length. Deliberately asserted as "at least one", not
    "exactly one": the count is a consequence of where the strokes stop, and pinning it exactly would
    make a re-styled mark look like a structural regression.

    THE SOUTH LIMIT IS THE FOOT, and that is the other half of this test. The strokes are allowed
    down to ``CANOPY_RAMP_FOOT_Y`` — 1.5 mm further south than the old keep-out — because the depth
    field reaches exactly zero there. South of it the roof IS the cover's 1.0 mm membrane, so a groove
    would be cutting through the part rather than into it."""
    crossing = [(s, i) for s in SIDES for i, seg in enumerate(segs[s])
                if min(p[1] for p in seg) < CAN.CANOPY_RAMP_TOP_Y]
    assert crossing, "no stroke crosses the ramp any more — re-justify the normal-offset cutter"
    y_min = min(p[1] for s in SIDES for seg in segs[s] for p in seg)
    assert y_min >= CAN.CANOPY_RAMP_FOOT_Y - 1e-9, \
        f"a stroke reaches y={y_min:.2f}, south of the ramp foot at {CAN.CANOPY_RAMP_FOOT_Y:.2f}"


# --------------------------------------------------------------------------------------------
# placement and safety
# --------------------------------------------------------------------------------------------

def _top_lines(side):
    """(west, north) chamfer top lines — the flat roof's own edge, i.e. each chamfer's PLAN run
    inboard of its wall. A stroke may run out TO these and no further.

    The two runs are not the same number, which is the whole reason ``canopy_north_chamfer_run``
    exists: the west facet runs 1.2 mm in and drops 2.4, the north chamfer does the opposite. Read
    them from ``canopy`` rather than recomputing, or this helper becomes a second opinion about the
    part's geometry."""
    return (CAN.CANOPY_WEST_OUTER_X + CAN.canopy_top_chamfer(side)[1],
            CAN.CANOPY_NORTH_OUTER_Y - CAN.canopy_north_chamfer_run(side))


@pytest.mark.parametrize("side", SIDES)
def test_every_terminal_is_either_on_an_edge_or_inside_the_safe_region(side, segs):
    """Each end is one of exactly two things, and nothing in between: OUT to an edge it is allowed
    to reach (the west/north chamfer top lines, or through the east arris for the upper stroke), or
    INSIDE the inset region. An end that stopped just short of an edge — inside the roof but outside
    the region — is the failure this catches: neither a terminal on a border nor a safe inset one,
    and it is what every stroke looked like before the breaks were added.

    The TERMINALS, meaning the first and last vertex. On a polyline every other vertex is interior by
    construction, and testing them all would demand that a bowed mark's mid-span satisfy a rule
    written for its ends."""
    x0, x1, _y0, y1 = CAN.canopy_puzzle_region(side)
    y0 = CAN.CANOPY_RAMP_FOOT_Y            # the curve's south bound — see ``_puzzle_strokes``
    x_w, y_n = _top_lines(side)
    n = PZ.upper_index(side, *CAN.canopy_puzzle_region(side))
    for i, seg in enumerate(segs[side]):
        x_max = CAN.canopy_puzzle_north_x1() if i == n else x1
        for x, y in (seg[0], seg[-1]):
            on_edge = x <= x_w + 1e-9 or y >= y_n - 1e-9 or x >= CAN.CANOPY_EAST_X
            inside = (x0 - 1e-9 <= x <= x_max + 1e-9) and (y0 - 1e-9 <= y <= y1 + 1e-9)
            assert on_edge or inside, (
                f"{side} line {i}: terminal ({x:.2f}, {y:.2f}) neither lands on a roof edge nor "
                f"sits in the safe region x {x0}..{x_max}, y {y0}..{y1}"
            )


@pytest.mark.parametrize("side", SIDES)
def test_every_stroke_runs_out_at_the_gap_side(side, segs):
    """THE point of the breaks. A line's two halves are collinear across the gap, but that only
    reads as one line if each segment leaves its roof at the gap-facing side rather than stopping in
    open roof and merely pointing at the other half.

    West is the gap-facing side for both halves (the canopy sits on each half's inner edge, and the
    left half is mirrored into place). One stroke is aimed too far north to reach the west line and
    borders the NORTH chamfer instead — also a roof edge, so it also counts."""
    x_w, y_n = _top_lines(side)
    for i, seg in enumerate(segs[side]):
        gap_end = min(seg, key=lambda p: p[0])
        assert gap_end[0] <= x_w + 1e-9 or gap_end[1] >= y_n - 1e-9, (
            f"{side} line {i}: the gap-side end ({gap_end[0]:.2f}, {gap_end[1]:.2f}) stops inside "
            f"the roof — the continuation across the gap will not read"
        )


@pytest.mark.parametrize("side", SIDES)
def test_at_most_one_stroke_reaches_north_and_it_is_aimed_past_the_wall(side, segs):
    """A stroke that reaches the north facet must be aimed PAST the wall, not stopped on the facet's
    top line. Not because it cuts that far — it does not; the cutter's floor is flat, so the groove
    fades out ~0.25 mm past the arris exactly as the west ends do — but because a stroke that stops
    ON the line ends in a square wall a hair short of the edge, and reads as a groove that gave up.
    Aimed past, the edge is what ends it.

    Pinned on the segment rather than on the built solid because that is where the distinction lives:
    both versions cut nearly the same material, and only the aim says which was intended."""
    y_n = _top_lines(side)[1]
    reach = [i for i, seg in enumerate(segs[side]) if max(p[1] for p in seg) > y_n]
    assert len(reach) <= 1, f"{side}: {len(reach)} strokes reach the north facet, expected at most 1"
    for i in reach:
        assert max(p[1] for p in segs[side][i]) > CAN.CANOPY_NORTH_OUTER_Y, (
            f"{side} line {i} stops on the facet at y={max(p[1] for p in segs[side][i]):.2f} — it "
            f"must run past the wall at {CAN.CANOPY_NORTH_OUTER_Y} to break the edge"
        )
        assert len(CAN.puzzle_north_crossings([segs[side][i]])) == 1


@pytest.mark.parametrize("side", SIDES)
def test_no_stroke_but_the_upper_one_leaves_through_the_east_wall(side, segs):
    """The east wall is the switch-column side, not the gap side, so at most ONE stroke per half is
    allowed out through it — the upper one. The other must die inboard: two east breaks would read
    as damage, not as a design.

    "At most", not "exactly", since the mark was curved: at A = 4.75 the left half's upper stroke no
    longer reaches that wall. Which half still has its break is pinned in the test below, so the
    weaker rule here cannot quietly become "none"."""
    n = PZ.upper_index(side, *CAN.canopy_puzzle_region(side))
    out = [i for i, seg in enumerate(segs[side]) if max(p[0] for p in seg) > CAN.CANOPY_EAST_X]
    assert out in ([], [n]), f"{side}: strokes crossing the east wall = {out}, expected [] or [{n}]"
    if out:
        assert max(p[0] for p in segs[side][n]) >= CAN.CANOPY_EAST_X + CAN.CANOPY_PUZZLE_W / 2, \
            f"{side}: the upper stroke's cap is not clear of the wall"


def test_the_pair_keeps_exactly_one_east_break_and_the_amplitude_is_what_cost_the_other(segs):
    """The straight mark notched the east arris ONCE PER HALF. The approved curve notches it once in
    the PAIR, on the right half, and the left half's upper stroke stops ~4.7 mm short in open roof
    (was 3.2 at A=4.75, now 4.7 at A=7) — still the bow lifting it off the wall.

    That was a deliberate trade when ``PUZZLE_CURVE_A`` was chosen — A ≈ 2.10 keeps both — so it is
    pinned here rather than left to be rediscovered as a regression. Attributed, too: the same stroke
    DOES reach the wall at A = 0, so the loss belongs to the amplitude and not to the nudge, the
    width or the clip. If someone re-tunes the amplitude down and both breaks come back, this test
    fails and asks them to say so."""
    east = [(side, i) for side in SIDES for i, seg in enumerate(segs[side])
            if max(p[0] for p in seg) > CAN.CANOPY_EAST_X]
    assert east == [("right", 1)], f"the pair's east breaks are {east}, expected only right line 1"

    short = CAN.CANOPY_EAST_X - max(p[0] for p in segs["left"][0])
    assert 4.0 < short < 5.5, \
        f"the left half's upper stroke now stops {short:.2f} mm short of the east wall, not ~4.7 (A=7)"

    saved = PZ.PUZZLE_CURVE_A
    try:
        PZ.PUZZLE_CURVE_A = 0.0
        flat = CAN.canopy_puzzle_strokes("left")
    finally:
        PZ.PUZZLE_CURVE_A = saved
    assert max(p[0] for p in flat[0]) > CAN.CANOPY_EAST_X, \
        "the left half's upper stroke misses the east wall even at zero amplitude — the break was " \
        "lost to something other than the curve, and that something is unaccounted for"


def test_the_north_exit_clears_the_corner_and_the_nudge_is_the_reason(segs):
    """``PUZZLE_LINE_NUDGE`` exists to move line A's exit out of the NW corner, and it is a hand-set
    number in a module where everything else is fitted — so pin what it buys, at both ends.

    As set, it must put the exit inside the safe window. Zeroed, the line must aim into the corner —
    otherwise the departure from the sketch is buying nothing and should be dropped. The window is
    derived in `canopy` from the corner radius and the pocket, so this test restates neither.

    Note what the zeroed case actually produces: the guard REFUSES the north break (the exit would
    be in the corner), so the stroke keeps the plain keep-out and never reaches the edge at all.
    That is the failure the nudge exists to avoid, and it is why the check below reads the line's
    own geometry rather than the finished terminals — the fallback would otherwise hide it."""
    x_lo, x_hi = CAN.canopy_puzzle_north_exit_window()
    crossings = [x for s in SIDES for x in CAN.puzzle_north_crossings(segs[s])]
    assert len(crossings) == 1, f"expected one stroke through the north wall, found {crossings}"
    assert all(len(CAN.puzzle_north_crossings([seg])) <= 1 for s in SIDES for seg in segs[s]), \
        "a stroke crosses the north wall twice — a curve can, and the window says nothing about it"
    x = crossings[0]
    assert x_lo <= x <= x_hi, f"the north exit at x={x:.2f} is outside the window {x_lo}..{x_hi}"

    def raw_exit(side, i):
        """Where line ``i`` crosses the north WALL, ignoring every keep-out."""
        a, b, c = PZ.line_in_canopy(side, i)
        return (c - b * CAN.CANOPY_NORTH_OUTER_Y) / a

    side, i = "right", 0
    # The curve leaves the wall within 0.6 µm of where its own BASELINE does — not a coincidence and
    # not something to assert as one: the exit sits essentially AT the seam (t −76.9 against the
    # seam's −75.9), where the odd-cubic profile passes through zero. So the amplitude cannot spend
    # the NW-corner clearance, however bold the mark gets out on the roof. Both facts are pinned,
    # because it is the second that makes the first safe.
    q = PZ.to_assembled((x, CAN.CANOPY_NORTH_OUTER_Y), side)
    assert abs(PZ.curve_lateral(i, PZ.curve_t(i, q))) < 0.01, (
        "the north exit has drifted off the seam, so the corner clearance now moves with "
        "PUZZLE_CURVE_A — re-measure it against the corner before trusting the window"
    )
    assert abs(raw_exit(side, i) - x) < 1e-3, "the pinned exit is not line 0's on the right half"

    # ...and the margin the corner actually gets, tilt included. The stroke meets the wall at 78.6°,
    # so its footprint ALONG the wall is (w/2)/sin θ = 0.51 mm per side rather than 0.50.
    seg = segs[side][i]
    tilt = max(abs(b[1] - a[1]) / math.dist(a, b) for a, b in zip(seg, seg[1:])
               if max(a[1], b[1]) >= CAN.CANOPY_NORTH_OUTER_Y > min(a[1], b[1]))
    half = (CAN.CANOPY_PUZZLE_W / 2) / tilt
    margin = x - half - (CAN.CANOPY_WEST_OUTER_X + CAN.CANOPY_CORNER_R)
    assert margin > 0.4, f"the groove's west edge clears the corner arc by only {margin:.2f} mm"
    saved = PZ.PUZZLE_LINE_NUDGE
    try:
        PZ.PUZZLE_LINE_NUDGE = (0.0,) * len(saved)
        bare_x = raw_exit(side, i)
        fell_back = [x for s in SIDES for x in CAN.puzzle_north_crossings(CAN.canopy_puzzle_strokes(s))]
    finally:
        PZ.PUZZLE_LINE_NUDGE = saved
    assert bare_x < x_lo, (
        f"without the nudge the line already exits at x={bare_x:.2f}, clear of the corner "
        f"({x_lo:.2f}) — the {saved[0]} mm departure from the sketch is buying nothing"
    )
    assert not fell_back, \
        "the un-nudged line was let out north anyway — the exit-window guard is not doing its job"


def test_the_nudge_did_not_cost_the_pairs_east_break(segs):
    """The other end of the nudge's window, and the one that is easy to miss: line A is shared, so
    pushing its right-half exit east slides the LEFT half's stroke north, towards the keep-out at its
    east end, until that stroke stops reaching the east wall and quietly loses its break — while the
    mark still looks fine on the right half, which is where anyone would be looking.

    The amplitude has since spent that particular break itself (see the test above), so what is left
    to protect is the pair's remaining one, on the right half. Checked at zero amplitude as well, so
    the nudge's own bound stays guarded rather than being masked by the curve: with the mark straight,
    BOTH halves must still break the arris at this nudge."""
    n = PZ.upper_index("right", *CAN.canopy_puzzle_region("right"))
    assert max(p[0] for p in segs["right"][n]) > CAN.CANOPY_EAST_X, \
        "right: the upper stroke no longer breaks the east arris"
    saved = PZ.PUZZLE_CURVE_A
    try:
        PZ.PUZZLE_CURVE_A = 0.0
        flat = {s: CAN.canopy_puzzle_strokes(s) for s in SIDES}
    finally:
        PZ.PUZZLE_CURVE_A = saved
    for side in SIDES:
        i = PZ.upper_index(side, *CAN.canopy_puzzle_region(side))
        assert max(p[0] for p in flat[side][i]) > CAN.CANOPY_EAST_X, \
            f"{side}: the nudge alone has now cost the east break, curve or no curve"


def test_the_stroke_that_reaches_the_north_chamfer_keeps_off_the_usb_pocket(segs):
    """One stroke borders the north chamfer, which puts its terminal inside the Y band the north
    keep-out exists to protect: the USB overmold pocket's roof has only CANOPY_USB_OM_ROOF_MIN
    (0.5 mm) of budget, i.e. exactly what a groove would spend. It is safe only because it lands
    WEST of the pocket — so pin that, rather than the fact that it currently happens to."""
    pocket_w = C.pcb_to_case(*C.MCU_POS)[0] - CAN.CANOPY_USB_OM_W / 2
    near = [(s, x) for s in SIDES for x in CAN.puzzle_north_crossings(segs[s])]
    assert near, "no stroke reaches the north wall any more — drop the y1_break plumbing"
    for s, x in near:
        assert x + CAN.CANOPY_PUZZLE_W / 2 + CAN.CANOPY_PUZZLE_POCKET_GAP <= pocket_w, \
            f"{s}: the north crossing at x={x:.2f} crowds the pocket (starts {pocket_w:.2f})"


@pytest.mark.parametrize("side", SIDES)
def test_the_safe_region_is_anchored_to_its_neighbours(side):
    """West measured from the roof edge the shoulder facet leaves, not the raw wall; north from the
    USB pocket's own roof budget."""
    x0, x1, y0, y1 = CAN.canopy_puzzle_region(side)
    facet_h = CAN.canopy_top_chamfer(side)[1]
    assert abs(x0 - (CAN.CANOPY_WEST_OUTER_X + facet_h + CAN.CANOPY_PUZZLE_LAND)) < 1e-9
    assert abs(x1 - (CAN.CANOPY_EAST_X - CAN.CANOPY_PUZZLE_LAND)) < 1e-9
    assert CAN.canopy_puzzle_north_x1() > CAN.CANOPY_EAST_X + CAN.CANOPY_PUZZLE_W / 2, \
        "the upper stroke's east bound no longer clears the wall by a full cap"
    assert y1 <= CAN.CANOPY_NORTH_OUTER_Y - CAN.CANOPY_USB_OM_DEPTH, \
        "the region reaches the USB overmold pocket's Y span"


def test_the_sketch_trims_shape_the_span_but_are_not_cut(segs):
    """``PUZZLE_STROKE_COVER`` is the sketch's own measurement of where each stroke STOPS (right line
    0 = 0.502 of its chord, left line 1 = 0.666), and it used to be applied to the cut geometry.

    It is not any more, and that was a decision rather than an oversight: the approved curve needs
    right line 0's full run to reach down the ramp at all, and the trims cost left line 1 nine of its
    24 mm. So the two trimmed strokes are cut at FULL length — asserted here, against the trim's own
    fraction, so nobody re-applies it by halves.

    What the trims still do is set ``PUZZLE_CURVE_SPAN``, via ``straight_strokes``. That is the whole
    reason the measurement survives in the module, and the reason this test checks the straight
    layout is still shorter than what is cut rather than deleting the constant outright."""
    straight = {s: CAN.straight_puzzle_strokes(s) for s in SIDES}
    for (side, i), f in PZ.PUZZLE_STROKE_COVER.items():
        cut_len = sum(math.dist(a, b) for a, b in zip(segs[side][i], segs[side][i][1:]))
        trimmed = math.dist(*straight[side][i])
        assert trimmed < cut_len * 0.9, (
            f"{side} line {i}: the straight layout ({trimmed:.1f} mm) is no longer the TRIMMED one "
            f"against a {cut_len:.1f} mm mark — the span's provenance has changed"
        )
        assert f < 1.0, f"{side} line {i}: a trim of {f:.3f} trims nothing"


def test_depth_is_derived_against_the_roof_thickness():
    assert CAN.CANOPY_PUZZLE_DEPTH + CAN.CANOPY_PUZZLE_MIN_ROOF <= CAN.CANOPY_ROOF_WALL + 1e-9


@pytest.mark.parametrize("side", SIDES)
def test_the_depth_ceiling_is_perpendicular_not_vertical(side):
    """``CANOPY_PUZZLE_DEPTH`` is only what the FLAT roof can spend.

    The cavity is a straight Z offset of the roofline, so on the ramp the shell measured PERPENDICULAR
    — the direction a groove eats — is only ``CANOPY_ROOF_WALL·cos θ``. The vertical arithmetic above
    is therefore true at θ = 0 and nowhere else, and it is why ``puzzle_depth_at`` exists: 1.5·cos
    34.9° = 1.23 mm on the right half's steepest run, where a full 0.5 mm groove would leave 0.73 of a
    roof that is supposed to keep 1.0.

    This is not hypothetical: before the field existed, the left half's line 1 dipped 3 mm into the
    ramp band and left 0.93 mm. Nothing failed, because the depth test measured normal to the surface
    and the roof test probed vertically."""
    z_ridge = CAN.canopy_ridge_top_z(side)
    y0, y1 = CAN.CANOPY_RAMP_FOOT_Y, CAN.CANOPY_RAMP_TOP_Y
    for k in range(int((y1 - y0) / 0.1) + 1):
        y = y0 + k * 0.1
        m = CAN._roofline_slope(y, z_ridge)
        k_ = math.sqrt(1 + m * m)
        d = CAN.puzzle_depth_at(y, z_ridge)
        assert d <= CAN.CANOPY_PUZZLE_DEPTH + 1e-9
        assert d <= CAN.CANOPY_ROOF_WALL / k_ - CAN.CANOPY_PUZZLE_MIN_ROOF + 1e-9, \
            f"{side}: {d:.3f} mm at y={y:.1f} leaves under {CAN.CANOPY_PUZZLE_MIN_ROOF} of shell"
        assert d <= (CAN._canopy_roof_z(y, z_ridge) - CAN.CANOPY_FUSE_BASE_Z) / k_ \
            - CAN.CANOPY_PUZZLE_MIN_ROOF + 1e-9, \
            f"{side}: {d:.3f} mm at y={y:.1f} eats into the cover membrane"


@pytest.mark.parametrize("side", SIDES)
def test_the_groove_dies_exactly_at_the_ramp_foot(side):
    """Not a fade someone chose — the foot IS the cover surface and the body's base is one cover
    thickness below it, so at the foot there is exactly ``CANOPY_PUZZLE_MIN_ROOF`` of material and the
    depth that survives is zero. Past it a groove would be cutting the 1.0 mm membrane."""
    z_ridge = CAN.canopy_ridge_top_z(side)
    assert CAN.puzzle_depth_at(CAN.CANOPY_RAMP_FOOT_Y, z_ridge) == 0.0
    assert CAN.puzzle_depth_at(CAN.CANOPY_RAMP_FOOT_Y - 5.0, z_ridge) == 0.0
    assert CAN.puzzle_depth_at(CAN.CANOPY_RAMP_TOP_Y, z_ridge) == CAN.CANOPY_PUZZLE_DEPTH


def test_the_two_halves_get_different_depth_fields():
    """A consequence, not a tuning: the ridges differ by 2.76 mm, so the ramps differ in slope, so the
    perpendicular shell — and the depth a groove may spend on it — differs too."""
    lo = min(CAN.puzzle_depth_at(y, CAN.canopy_ridge_top_z("left")) for y in
             [CAN.CANOPY_RAMP_FOOT_Y + k * 0.1 for k in range(228)])
    ro = min(CAN.puzzle_depth_at(y, CAN.canopy_ridge_top_z("right")) for y in
             [CAN.CANOPY_RAMP_FOOT_Y + 5.0 + k * 0.1 for k in range(178)])
    assert abs(lo - 0.0) < 1e-9, "the left field no longer reaches zero at the foot"
    assert 0.22 < ro < 0.24, f"the right half's steepest point now allows {ro:.3f} mm"


# --------------------------------------------------------------------------------------------
# on the part
# --------------------------------------------------------------------------------------------

@pytest.mark.parametrize("side", SIDES)
def test_cut_canopy_is_still_one_valid_solid(side, cut):
    c = cut[side]
    assert len(c.solids()) == 1
    assert BRepCheck_Analyzer(c.wrapped).IsValid()


@pytest.mark.parametrize("side", SIDES)
def test_ridge_and_footprint_are_untouched(side, bare, cut):
    a, b = bare[side].bounding_box(), cut[side].bounding_box()
    for name, va, vb in (("max Z", a.max.Z, b.max.Z), ("min X", a.min.X, b.min.X),
                         ("max X", a.max.X, b.max.X), ("max Y", a.max.Y, b.max.Y),
                         ("min Y", a.min.Y, b.min.Y)):
        assert abs(va - vb) < 1e-6, f"{side}: the strokes moved the {name} ({va:.3f} → {vb:.3f})"


@pytest.mark.parametrize("side", SIDES)
def test_each_stroke_is_cut_to_depth_along_its_whole_length(side, cut, segs):
    """Normal to the surface, at 13 stations per stroke, against the depth the SURFACE allows there.

    Compared with ``puzzle_depth_at`` rather than with a constant, because the groove is only 0.5 mm
    deep where the roof is flat: on the ramp the perpendicular shell is thinner and the mark shallows
    to keep ``CANOPY_PUZZLE_MIN_ROOF``. The cutter and this test therefore read the SAME function, so
    "is the groove the right depth" stops being two independent opinions.

    The band allows the ramp Spline's own documented ±0.032 mm deviation, which errs SHALLOW — the roof
    ends up thicker, never thinner. Stations whose allowed depth is under 0.10 mm are skipped and
    counted: a 0.08 mm probe column cannot resolve them, and silently skipping all of them would let
    an uncut stroke pass."""
    z_ridge = CAN.canopy_ridge_top_z(side)
    for i, seg in enumerate(segs[side]):
        probed = 0
        stations = _stations(side, seg, 13, 0.04, 0.96)
        for x, y in stations:
            want = CAN.puzzle_depth_at(y, z_ridge)
            if want < 0.10:
                continue                      # below what the probe column can measure
            probed += 1
            d = _normal_depth(cut[side], x, y, z_ridge)
            assert d is not None, f"{side} line {i}: no material at ({x:.2f}, {y:.2f})"
            assert want - 0.06 < d <= want + 0.03, (
                f"{side} line {i}: {d:.3f} mm normal depth at ({x:.2f}, {y:.2f}), "
                f"expected ≈{want:.3f} (the depth this surface allows)"
            )
        assert probed >= len(stations) // 3, \
            f"{side} line {i}: only {probed} of {len(stations)} stations were deep enough to measure"


@pytest.mark.parametrize("side", SIDES)
def test_roof_survives_under_every_stroke(side, cut, segs):
    """Measured PERPENDICULAR to the surface, which is the direction that matters and the direction
    this test used to get wrong: probing a fixed distance straight down under-reads the loss on a
    slope by cos θ, so a groove could eat into ``CANOPY_PUZZLE_MIN_ROOF`` on the ramp and this test
    would still find material. It did, before the depth field: 0.93 mm under the left half's line 1."""
    z_ridge = CAN.canopy_ridge_top_z(side)
    for i, seg in enumerate(segs[side]):
        for x, y in _stations(side, seg, 9):
            floor = _roof_top(cut[side], x, y)
            assert floor is not None, f"{side} line {i}: nothing at ({x:.2f}, {y:.2f})"
            m = CAN._roofline_slope(y, z_ridge)
            k = math.sqrt(1 + m * m)
            # What survives under the groove, perpendicular: the shell less what the groove took out
            # of it, or — near the foot — the distance down to the body's own base.
            vcut = CAN._canopy_roof_z(y, z_ridge) - floor
            left = min(CAN.CANOPY_ROOF_WALL - vcut, floor - CAN.CANOPY_FUSE_BASE_Z) / k
            assert left >= CAN.CANOPY_PUZZLE_MIN_ROOF - 0.04, (
                f"{side} line {i}: only {left:.3f} mm left under the groove at ({x:.2f}, {y:.2f})"
            )
            assert _solid_at(cut[side], x, y, floor - 0.3, s=0.12), \
                f"{side} line {i}: roof pierced at ({x:.2f}, {y:.2f})"


@pytest.mark.parametrize("side", SIDES)
def test_no_terminal_is_rounded(side, bare, cut, segs):
    """Every stroke ends square — as if a knife lifted off it. A rounded cap reads as a blob at the
    end of a thin line, and it shows most on exactly the ends that stop in open roof.

    Asserted as "the strokes introduced no cylindrical face at all", which is stronger than counting
    caps and needs no bookkeeping about which ends are free: the cutter is a plain box prism, so a
    cylinder appearing here means a stadium cutter came back."""
    def keys(part):
        return {(round(f.center().X, 2), round(f.center().Y, 2), round(f.center().Z, 2),
                 round(f.area, 3)) for f in part.faces()}
    old = keys(bare[side])
    new_cyls = [f for f in cut[side].faces()
                if f.geom_type == GeomType.CYLINDER
                and (round(f.center().X, 2), round(f.center().Y, 2), round(f.center().Z, 2),
                     round(f.area, 3)) not in old]
    assert not new_cyls, (
        f"{side}: {len(new_cyls)} rounded stroke terminal(s) at "
        f"{[(round(f.center().X, 1), round(f.center().Y, 1)) for f in new_cyls]}"
    )
    # ...and the strokes really are there, so the assert above cannot pass by cutting nothing.
    assert bare[side].volume - cut[side].volume > 10.0


@pytest.mark.parametrize("side", SIDES)
def test_strokes_keep_off_the_facet_corner_and_usb_pocket(side, bare, cut, segs):
    """The strokes leave the west edge cleanly and fade onto the drafted facet.

    The cutter deliberately runs past the facet's top line: it keeps a square-free terminal at the
    edge, then loses depth as the facet drops away below the normal-offset groove floor. Probe the
    flat shoulder for unwanted cuts and the facet separately for that intentional partial cut.
    """
    xw = CAN.CANOPY_WEST_OUTER_X
    x_top = _top_lines(side)[0]
    for i, seg in enumerate(segs[side]):
        if min(p[0] for p in seg) > x_top + 0.05:
            continue                       # this stroke never gets to the facet
        for x in (xw + 0.2, xw + 0.6):
            y = _y_at_x(seg, x)
            assert y is not None, f"{side} line {i}: does not reach x={x:.2f}"
            a, b = _roof_top(bare[side], x, y), _roof_top(cut[side], x, y)
            assert (a is None) == (b is None)
            if a is not None:
                assert abs(a - b) < 1e-6, (
                    f"{side} line {i}: cut before reaching the west facet at "
                    f"({x:.2f}, {y:.1f}) — {a:.3f} → {b:.3f}"
                )
        x = x_top - 0.15
        y = _y_at_x(seg, x)
        assert y is not None, f"{side} line {i}: does not reach the facet's top line"
        a, b = _roof_top(bare[side], x, y), _roof_top(cut[side], x, y)
        assert (a is None) == (b is None)
        if a is not None:
            fade = a - b
            assert 0.0 < fade < CAN.puzzle_depth_at(y, CAN.canopy_ridge_top_z(side)) + 0.03, (
                f"{side} line {i}: facet terminal did not fade correctly at "
                f"({x:.2f}, {y:.1f}) — {fade:.3f} mm"
            )
    r = CAN.CANOPY_CORNER_R
    corner = [f for f in cut[side].faces()
              if f.center().X < xw + r and f.center().Y > CAN.CANOPY_NORTH_OUTER_Y - r]
    kinds = sorted({str(f.geom_type).split(".")[-1] for f in corner})
    assert kinds == ["CYLINDER"], f"{side}: the strokes disturbed the NW corner round: {kinds}"
    ucx = C.pcb_to_case(*C.MCU_POS)[0]
    pocket_top = CAN.canopy_usb_om_z(side)[1]
    y_pocket = CAN.CANOPY_NORTH_OUTER_Y - CAN.CANOPY_USB_OM_DEPTH / 2
    assert _solid_at(cut[side], ucx, y_pocket, pocket_top + 0.25, s=0.2), \
        f"{side}: material missing above the USB pocket"


@pytest.mark.parametrize("side", SIDES)
def test_the_east_arris_is_broken_at_most_once_per_half(side, bare, cut, segs):
    """Where a stroke runs into the wall bordering the switch columns, that arris IS notched — once,
    where that stroke crosses it, and nowhere else. Probed at 0.25 mm steps: a groove 1.0 mm wide
    cannot hide between stations, so a second notch (a lower stroke that drifted east, or a cutter
    overshooting in the wrong place) shows up as a second run of cut Y.

    On the left half the expected count is now ZERO — the curve lifted its upper stroke off that
    wall — so this test derives what it expects from the strokes instead of assuming one. An
    UNCUT arris where a stroke does reach it, and a cut one where none does, both fail; which half
    is which is pinned separately, in
    ``test_the_pair_keeps_exactly_one_east_break_and_the_amplitude_is_what_cost_the_other``.

    EAST is now chamfered like the west (``_chamfer_east_top``), so a stroke that runs past the
    east wall FADES over the 1.2 mm × 2.4 mm facet rather than notching a sharp arris. The flat
    roof just inboard of the facet top line is still cut, but the chamfer face itself is not —
    which is the same terminus the west strokes have. The probe therefore sits on the chamfer
    slope (``EAST_X - 0.4``) where a sharp notch would show and a fade shows nothing."""
    probe_x = CAN.CANOPY_EAST_X - 0.4
    z_ridge = CAN.canopy_ridge_top_z(side)
    breakers = [i for i, seg in enumerate(segs[side])
                if max(p[0] for p in seg) > CAN.CANOPY_EAST_X]
    cut_ys = []
    y = 62.0
    while y <= 118.0:
        a, b = _roof_top(bare[side], probe_x, y), _roof_top(cut[side], probe_x, y)
        assert (a is None) == (b is None)
        if a is not None and abs(a - b) > 1e-6:
            m = CAN._roofline_slope(y, z_ridge)
            d = (a - b) / math.sqrt(1 + m * m)
            allowed = CAN.puzzle_depth_at(y, z_ridge)
            assert d <= allowed + 0.03, \
                f"{side}: the arris is notched {d:.3f} mm deep at y={y}, allowed {allowed:.3f}"
            cut_ys.append(y)
        y += 0.25

    runs = []
    for y in cut_ys:
        if runs and y - runs[-1][-1] < 0.5:
            runs[-1].append(y)
        else:
            runs.append([y])
    # East now carries the same drafted facet as the west, so the chamfer face itself is NOT
    # notched — a stroke past the wall fades over it like the west strokes do. The flat roof
    # just inboard of the top line is still cut, but this probe sits on the slope to verify
    # the facade stays intact.
    assert len(runs) == 0, (
        f"{side}: the east chamfer face is notched in {len(runs)} place(s) "
        f"({[(r[0], r[-1]) for r in runs]}); with the east facet the groove should fade, "
        f"not cut the chamfer (stroke(s) past the wall: {breakers})"
    )


def test_strokes_do_not_detonate_the_mesh():
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.BRep import BRep_Tool
    from OCP.TopLoc import TopLoc_Location

    c = build_canopy(side="right")
    BRepMesh_IncrementalMesh(c.wrapped, 1e-3, False, 0.1, True)
    n = 0
    for f in c.faces():
        tri = BRep_Tool.Triangulation_s(f.wrapped, TopLoc_Location())
        n += tri.NbTriangles() if tri is not None else 0
    assert n < 200_000, f"canopy meshes to {n} triangles"


@pytest.mark.parametrize("side", SIDES)
def test_strokes_survive_the_fuse_into_the_top(side, segs):
    """The canopy is fused into the TOP, so the strokes must still be there — the cover union is
    exactly the kind of step that could backfill shallow surface detail.

    Sampled ALONG the polyline and compared against ``puzzle_depth_at``, not against a flat 0.4 mm
    floor: the mark shallows on the ramp by design, so a fixed floor would now read the ramp's own
    run-out as a backfilled groove."""
    top = build_top_part(side)
    assert len(top.solids()) == 1
    z_ridge = CAN.canopy_ridge_top_z(side)
    for i, seg in enumerate(segs[side]):
        found = []
        for k in range(9):
            x, y = _walk(seg, 0.05 + 0.9 * k / 8)
            want = CAN.puzzle_depth_at(y, z_ridge)
            if want < 0.10:
                continue                      # on the ramp's run-out; nothing to measure here
            if side == "left":
                x = C.OUTER_WIDTH - x
            tz = _roof_top(top, x, y)
            if tz is not None:
                m = CAN._roofline_slope(y, z_ridge)
                found.append(((CAN._canopy_roof_z(y, z_ridge) - tz) / math.sqrt(1 + m * m), want))
        assert found and all(d > w - 0.06 for d, w in found), \
            f"{side} line {i}: not intact on the TOP — {[(round(d, 3), round(w, 3)) for d, w in found]}"
