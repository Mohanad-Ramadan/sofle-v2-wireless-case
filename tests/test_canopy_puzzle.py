"""Tests for the canopy roofs' PUZZLE strokes — two lines that each cross BOTH halves.

The design's whole claim is that the four strokes are really two straight lines seen in two splayed
frames, so the mark completes only when both halves are on the desk. These tests pin that claim and
the things that could quietly break it:

  1. COLLINEARITY in the assembled frame. This must be exact (0 mm), because the strokes are cut
     from one line rather than aimed at each other — if it ever becomes merely small, someone has
     started transcribing angles instead of deriving them.
  2. The two halves must NOT match. That is a consequence of the design, not a decoration: one line
     meets each canopy at a different angle. If the halves ever agree, the splay has gone to zero and
     the idea has collapsed.
  3. A stroke CROSSES THE RAMP, which is why the cutter clips against a NORMAL-offset roofline
     instead of measuring depth vertically. A test pins that one still does, so the construction
     cannot be "simplified" to a vertical drop without a failure.
  3b. Where each stroke STOPS is measured from the sketch too (`PUZZLE_STROKE_COVER`), not chosen —
     the line fit says nothing about extent.
  4. Terminals. Every stroke runs out to the roof's own edge on the gap side (the west chamfer's top
     line, or the north one for the stroke aimed too far north to reach it) so the continuation
     across the gap reads; each half's UPPER stroke additionally breaks THROUGH the east arris, the
     switch-column side, which is the only edge actually notched. Ends are square, never rounded.

Depth is asserted NORMAL to the surface, never vertically: the right half's ramp tips to 35.9°, where
a vertical measurement of a 0.5 mm groove reads 0.62 mm.
"""
import math

import pytest
import numpy as np
from build123d import Solid, GeomType
from OCP.BRepCheck import BRepCheck_Analyzer

from sofle_case import constants as C
from sofle_case import canopy as CAN
from sofle_case import canopy_puzzle as PZ
from sofle_case.canopy import build_canopy
from sofle_case.case import build_top_part

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


def _stations(side, seg, n, lo=0.05, hi=0.95):
    """``n`` sample points along a stroke, dropping the ones that are not on the flat roof.

    Every stroke now runs OUT of the roof at one end or both, so its extreme stations are either in
    open air (past the east wall / the north wall) or on the west shoulder facet, where the surface
    has already fallen away below the cutter. A probe there measures nothing and would read as a
    missing groove. Bounded by the geometry rather than by a fixed t, so the surviving stations still
    reach right up to each break."""
    x_w = CAN.CANOPY_WEST_OUTER_X + CAN.canopy_top_chamfer(side)[1] + 0.3   # past the facet arris
    (x0, y0), (x1, y1) = seg
    out = []
    for k in range(n):
        t = lo + (hi - lo) * k / (n - 1)
        x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
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

def test_the_two_halves_strokes_are_exactly_collinear_when_assembled(segs):
    """THE test for this feature. Each line's four endpoints — two from each half — must lie on one
    straight line to numerical zero, because they are segments OF that line. Anything above ~1e-9
    means the derivation has been replaced by transcription somewhere."""
    spread = PZ.assembled_offline_spread(segs)
    for i, s in enumerate(spread):
        assert s < 1e-6, f"line {i}: endpoints deviate {s:.6f} mm from a single straight line"


def test_redesigning_at_a_different_separation_stays_exact(segs):
    """DESIGN-time: the separation is an input that decides where the lines cross each roof. Changing
    it must re-place the strokes and keep collinearity exact — that is what makes the layout a derived
    quantity rather than four tuned numbers.

    The usable design window is about +8 mm; past ~12 mm line 0 slides off the right roof entirely,
    at which point ``strokes`` raises rather than silently emitting nothing."""
    saved = PZ.PUZZLE_RIGHT_OFFSET
    try:
        for d in (-6.0, 4.0, 8.0):
            PZ.PUZZLE_RIGHT_OFFSET = (saved[0] + d, saved[1])
            moved = {s: CAN.canopy_puzzle_strokes(s) for s in SIDES}
            assert moved["right"] != segs["right"], f"{d:+} mm should re-place the strokes"
            for i, s in enumerate(PZ.assembled_offline_spread(moved)):
                assert s < 1e-6, f"line {i} lost collinearity at {d:+} mm ({s:.2e} mm)"
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
    With a 1.6 mm groove, line 0 still reads as joined for about ±1 mm of misplacement and line 1 for
    about ±18 mm. Keeping ONE forgiving line in the pair is deliberate: the design degrades by half
    rather than all at once."""
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


def test_the_halves_are_not_alike(segs):
    """A consequence of the splay, not a styling choice — so assert it as a consequence."""
    assert segs["left"] != segs["right"]
    for i in range(len(PZ.PUZZLE_LINES)):
        dl = (segs["left"][i][1][0] - segs["left"][i][0][0]) / \
             (segs["left"][i][1][1] - segs["left"][i][0][1])
        dr = (segs["right"][i][1][0] - segs["right"][i][0][0]) / \
             (segs["right"][i][1][1] - segs["right"][i][0][1])
        assert abs(dl - dr) > 0.5, \
            f"line {i}: the halves meet it at nearly the same angle ({dl:+.3f} vs {dr:+.3f}) — " \
            f"the splay has collapsed and the halves now look alike"


def test_canopy_line_and_assembled_line_agree(segs):
    """``line_in_canopy`` and ``to_assembled`` are two views of one line; a point satisfying the
    canopy-frame equation must land on the assembled-frame line. If these ever disagree the strokes
    would still be drawn, just not where the design says."""
    for side in SIDES:
        for i, (ang, off) in enumerate(PZ.PUZZLE_LINES):
            a, b, c = PZ.line_in_canopy(side, i)
            th = math.radians(ang)
            n = (math.cos(th), -math.sin(th))
            for p in segs[side][i]:
                assert abs(a * p[0] + b * p[1] - c) < 1e-9, \
                    f"{side} line {i}: endpoint {p} is off its own canopy-frame equation"
                q = PZ.to_assembled(p, side)
                assert abs(n[0] * q[0] + n[1] * q[1] - off) < 1e-9, \
                    f"{side} line {i}: endpoint {p} misses the assembled line"


def test_a_stroke_still_crosses_the_ramp(segs):
    """Which is why the cutter clips against a NORMAL-offset roofline. If this ever drops to ZERO,
    the vertical-depth shortcut starts looking safe — and it is not, because on the 35.9° ramp it
    thins a 0.5 mm groove to 0.40, i.e. it would go shallow exactly where the surface is most
    visible while still passing any "did it cut?" check.

    It was two strokes until the right half's line 0 was trimmed to its sketched half-chord; that
    pulled its free end off the ramp and onto the flat roof. Deliberately asserted as "at least
    one", not "exactly one": the count is a consequence of where the strokes stop, and pinning it
    exactly would make an aesthetic trim look like a structural regression."""
    crossing = [(s, i) for s in SIDES for i, seg in enumerate(segs[s])
                if min(p[1] for p in seg) < CAN.CANOPY_RAMP_TOP_Y]
    assert crossing, "no stroke crosses the ramp any more — re-justify the normal-offset cutter"


# --------------------------------------------------------------------------------------------
# placement and safety
# --------------------------------------------------------------------------------------------

@pytest.mark.parametrize("side", SIDES)
def _top_lines(side):
    """(west, north) chamfer top lines — the flat roof's own edge, one horizontal chamfer leg
    inboard of each wall. A stroke may run out TO these and no further."""
    h = CAN.canopy_top_chamfer(side)[1]
    return CAN.CANOPY_WEST_OUTER_X + h, CAN.CANOPY_NORTH_OUTER_Y - h


@pytest.mark.parametrize("side", SIDES)
def test_every_terminal_is_either_on_an_edge_or_inside_the_safe_region(side, segs):
    """Each end is one of exactly two things, and nothing in between: OUT to an edge it is allowed
    to reach (the west/north chamfer top lines, or through the east arris for the upper stroke), or
    INSIDE the inset region. An end that stopped just short of an edge — inside the roof but outside
    the region — is the failure this catches: neither a terminal on a border nor a safe inset one,
    and it is what every stroke looked like before the breaks were added."""
    x0, x1, y0, y1 = CAN.canopy_puzzle_region(side)
    x_w, y_n = _top_lines(side)
    n = PZ.upper_index(side, *CAN.canopy_puzzle_region(side))
    for i, seg in enumerate(segs[side]):
        x_max = CAN.canopy_puzzle_north_x1() if i == n else x1
        for x, y in seg:
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
def test_no_stroke_crosses_the_north_chamfer_top_line(side, segs):
    """NORTH only, and the asymmetry is the point. West is aimed past the wall: the shoulder facet
    falls away from the swept roofline at 2:1, so the groove simply runs off the arris and stops
    ~0.25 mm later — nothing to protect there. North is different: past that line the mark crosses
    the NW corner round and heads for the USB pocket's 0.5 mm roof budget, so the stroke is stopped
    ON the line and borders the chamfer."""
    y_n = _top_lines(side)[1]
    for i, seg in enumerate(segs[side]):
        for _x, y in seg:
            assert y <= y_n + 1e-9, f"{side} line {i}: y={y:.2f} is past the north top line {y_n}"


@pytest.mark.parametrize("side", SIDES)
def test_only_the_upper_stroke_leaves_through_the_east_wall(side, segs):
    """The east wall is the switch-column side, not the gap side, so exactly ONE stroke per half is
    allowed out through it — the upper one. The other must die inboard: two east breaks would read
    as damage, not as a design."""
    n = PZ.upper_index(side, *CAN.canopy_puzzle_region(side))
    out = [i for i, seg in enumerate(segs[side]) if max(p[0] for p in seg) > CAN.CANOPY_EAST_X]
    assert out == [n], f"{side}: strokes crossing the east wall = {out}, expected only {n}"
    (ax, _), (bx, _) = segs[side][n]
    assert max(ax, bx) >= CAN.CANOPY_EAST_X + CAN.CANOPY_PUZZLE_W / 2, \
        f"{side}: the upper stroke's cap is not clear of the wall"


def test_the_stroke_that_reaches_the_north_chamfer_keeps_off_the_usb_pocket(segs):
    """One stroke borders the north chamfer, which puts its terminal inside the Y band the north
    keep-out exists to protect: the USB overmold pocket's roof has only CANOPY_USB_OM_ROOF_MIN
    (0.5 mm) of budget, i.e. exactly what a groove would spend. It is safe only because it lands
    WEST of the pocket — so pin that, rather than the fact that it currently happens to."""
    pocket_w = C.pcb_to_case(*C.MCU_POS)[0] - CAN.CANOPY_USB_OM_W / 2
    near = [(s, i, p) for s in SIDES for i, seg in enumerate(segs[s]) for p in seg
            if p[1] > CAN.CANOPY_NORTH_OUTER_Y - CAN.CANOPY_USB_OM_DEPTH]
    assert near, "no stroke reaches the north chamfer any more — drop the y1_break plumbing"
    for s, i, (x, _y) in near:
        assert x + CAN.CANOPY_PUZZLE_W / 2 + CAN.CANOPY_PUZZLE_POCKET_GAP <= pocket_w, \
            f"{s} line {i}: the terminal at x={x:.2f} crowds the pocket (starts {pocket_w:.2f})"


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


def test_a_trimmed_stroke_covers_its_sketched_fraction(segs):
    """The sketch fixes where a stroke STOPS as well as where it runs; ``PUZZLE_STROKE_COVER`` is
    that measurement (right line 0 = 0.502 of its chord). Pinned as a FRACTION, because the mm length
    moves with the region and the breaks while the drawing's proportion does not — and measured
    against the stroke's own full run, anchored at the north end, so the trim can only take the free
    south terminal back.

    The full run is recovered by disabling the trim rather than recomputing a chord by hand: that way
    the test cannot drift out of step with how ``strokes`` actually clips."""
    saved = PZ.PUZZLE_STROKE_COVER
    try:
        PZ.PUZZLE_STROKE_COVER = {}
        untrimmed = {s: CAN.canopy_puzzle_strokes(s) for s in SIDES}
    finally:
        PZ.PUZZLE_STROKE_COVER = saved

    for (side, i), f in PZ.PUZZLE_STROKE_COVER.items():
        full, seg = untrimmed[side][i], segs[side][i]
        assert math.dist(*seg) / math.dist(*full) == pytest.approx(f, abs=0.005), \
            f"{side} line {i} no longer covers {f:.1%} of its run"
        assert seg[1] == pytest.approx(full[1]), \
            f"{side} line {i}: the trim moved the ANCHORED (north) end, not the free one"
        assert math.dist(seg[0], full[0]) > 1.0, f"{side} line {i}: the trim did nothing"


def test_depth_is_derived_against_the_roof_thickness():
    assert CAN.CANOPY_PUZZLE_DEPTH + CAN.CANOPY_PUZZLE_MIN_ROOF <= CAN.CANOPY_ROOF_WALL + 1e-9


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
    """Normal to the surface, at 13 stations per stroke. The band's lower edge allows the ramp
    Spline's own documented ±0.032 mm deviation, which errs SHALLOW — the roof ends up thicker,
    never thinner."""
    z_ridge = CAN.canopy_ridge_top_z(side)
    for i, seg in enumerate(segs[side]):
        for x, y in _stations(side, seg, 13, 0.04, 0.96):
            d = _normal_depth(cut[side], x, y, z_ridge)
            assert d is not None, f"{side} line {i}: no material at ({x:.2f}, {y:.2f})"
            assert 0.44 < d <= CAN.CANOPY_PUZZLE_DEPTH + 0.03, (
                f"{side} line {i}: {d:.3f} mm normal depth at ({x:.2f}, {y:.2f}), "
                f"expected ≈{CAN.CANOPY_PUZZLE_DEPTH}"
            )


@pytest.mark.parametrize("side", SIDES)
def test_roof_survives_under_every_stroke(side, cut, segs):
    z_ridge = CAN.canopy_ridge_top_z(side)
    for i, seg in enumerate(segs[side]):
        for x, y in _stations(side, seg, 9):
            surf = CAN._canopy_roof_z(y, z_ridge)
            assert _solid_at(cut[side], x, y, surf - CAN.CANOPY_PUZZLE_DEPTH - 0.3, s=0.12), \
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
    """The strokes stop ON the west chamfer's top line, so the facet SURFACE below it must be
    untouched. Probed along each stroke's own line — where it actually approaches the facet — not at
    fixed Y stations that a re-fit could slide the strokes away from."""
    xw = CAN.CANOPY_WEST_OUTER_X
    x_top = _top_lines(side)[0]
    for i, ((ax, ay), (bx, by)) in enumerate(segs[side]):
        if min(ax, bx) > x_top + 0.05:
            continue                       # this stroke never gets to the facet
        for x in (xw + 0.2, xw + 0.6, x_top - 0.15):
            y = ay + (by - ay) * (x - ax) / (bx - ax)
            a, b = _roof_top(bare[side], x, y), _roof_top(cut[side], x, y)
            assert (a is None) == (b is None)
            if a is not None:
                assert abs(a - b) < 1e-6, (
                    f"{side} line {i}: crossed onto the west shoulder facet at "
                    f"({x:.2f}, {y:.1f}) — {a:.3f} → {b:.3f}"
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
def test_the_east_arris_is_broken_exactly_once(side, bare, cut, segs):
    """The upper stroke runs into the wall bordering the switch columns, so that arris IS notched —
    once, where that stroke crosses it, and nowhere else. Probed at 0.5 mm steps: a groove 1.6 mm
    wide cannot hide between stations, so a second notch (a lower stroke that drifted east, or a
    cutter overshooting in the wrong place) shows up as a second run of cut Y."""
    probe_x = CAN.CANOPY_EAST_X - 0.4
    z_ridge = CAN.canopy_ridge_top_z(side)
    cut_ys = []
    y = 62.0
    while y <= 118.0:
        a, b = _roof_top(bare[side], probe_x, y), _roof_top(cut[side], probe_x, y)
        assert (a is None) == (b is None)
        if a is not None and abs(a - b) > 1e-6:
            m = CAN._roofline_slope(y, z_ridge)
            d = (a - b) / math.sqrt(1 + m * m)
            assert d <= CAN.CANOPY_PUZZLE_DEPTH + 0.03, \
                f"{side}: the arris is notched {d:.3f} mm deep at y={y}, not {CAN.CANOPY_PUZZLE_DEPTH}"
            cut_ys.append(y)
        y += 0.5

    runs = []
    for y in cut_ys:
        if runs and y - runs[-1][-1] < 0.75:
            runs[-1].append(y)
        else:
            runs.append([y])
    assert len(runs) == 1, \
        f"{side}: the east arris is cut in {len(runs)} places ({[ (r[0], r[-1]) for r in runs ]})"

    # ...and it is the UPPER stroke that did it, at the Y where that stroke crosses the wall.
    (ax, ay), (bx, by) = segs[side][PZ.upper_index(side, *CAN.canopy_puzzle_region(side))]
    t = (CAN.CANOPY_EAST_X - ax) / (bx - ax)
    y_expect = ay + (by - ay) * t
    y_mid = (runs[0][0] + runs[0][-1]) / 2
    assert abs(y_mid - y_expect) < CAN.CANOPY_PUZZLE_W, \
        f"{side}: the notch sits at y≈{y_mid:.2f}, the upper stroke crosses at {y_expect:.2f}"


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
    exactly the kind of step that could backfill shallow surface detail."""
    top = build_top_part(side)
    assert len(top.solids()) == 1
    z_ridge = CAN.canopy_ridge_top_z(side)
    for i, ((x0, y0), (x1, y1)) in enumerate(segs[side]):
        found = []
        for k in range(9):
            t = 0.05 + 0.9 * k / 8
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            if side == "left":
                x = C.OUTER_WIDTH - x
            tz = _roof_top(top, x, y)
            if tz is not None:
                m = CAN._roofline_slope(y, z_ridge)
                found.append((CAN._canopy_roof_z(y, z_ridge) - tz) / math.sqrt(1 + m * m))
        assert found and all(d > 0.4 for d in found), \
            f"{side} line {i}: not intact on the TOP — {[round(d, 3) for d in found]}"
