"""M17-3 connection mark on the removable MCU/encoder covers."""
from __future__ import annotations

import math
from itertools import pairwise

import pytest
from build123d import Part, Pos, Solid, extrude

from sofle_case import constants as C
from sofle_case import cover_mark as CM
from sofle_case import mcu_encoder_cover as MEC
from tests.shared_builds import build_mcu_encoder_cover
from tests.test_clearances import _sided

SIDES = ("right", "left")
GOLDEN_CURVE = {
    -120: (185.544716, -13.138593), -90: (182.048006, 21.4502),
    -76: (174.392364, 33.194957), -60: (165.808219, 46.738083),
    -30: (162.037296, 81.126735),
}
GOLDEN_NARROWS_U = (-39.944383, -10.044494, 20.011123)
GOLDEN_NARROWS = {
    # u = -10.04 sits inside the fan's +/-FAN_BLEND ease, so it moves off the preview by design.
    18.5: (41.076689, 36.854633, 22.03113),
    31.0: (50.464589, 40.292966, 38.582579),
    43.5: (59.852489, 43.731299, 55.134029),
}


def _bounds() -> tuple[float, float, float, float]:
    outer = MEC._cover_outer_polygon()
    xs, ys = [x for x, _ in outer], [y for _, y in outer]
    return (min(xs)-2, max(xs)+2, min(ys)-2, max(ys)+2)


def _seg_dist(p, a, b) -> float:
    dx, dy = b[0]-a[0], b[1]-a[1]
    length2 = dx*dx+dy*dy
    t = 0.0 if length2 == 0 else min(1.0, max(0.0, ((p[0]-a[0])*dx+(p[1]-a[1])*dy)/length2))
    return math.dist(p, (a[0]+t*dx, a[1]+t*dy))


def _dist_to_polyline(p, poly) -> float:
    return min(_seg_dist(p, a, b) for a, b in pairwise(poly))


def _probe(x: float, y: float, z: float, size: float = 0.2) -> Solid:
    return Solid.make_box(size, size, size).translate((x-size/2, y-size/2, z-size/2))


@pytest.fixture(scope="module")
def marked() -> dict[str, Part]:
    return {side: build_mcu_encoder_cover(side) for side in SIDES}


@pytest.fixture(scope="module")
def bare() -> dict[str, Part]:
    return {side: MEC.build_mcu_encoder_cover(side, mark=False) for side in SIDES}


@pytest.fixture(scope="module")
def strokes() -> dict[str, list]:
    return {side: CM.strokes(side, MEC._mark_inside(side)) for side in SIDES}


def test_curve_and_narrows_match_approved_preview_formulas():
    for t, (x, y) in GOLDEN_CURVE.items():
        px, py = CM._curve_point(t)
        assert px == pytest.approx(x, abs=1e-3) and py == pytest.approx(y, abs=1e-3)
    half = CM.design_frame()[3]
    for v0, expected in GOLDEN_NARROWS.items():
        for u, value in zip(GOLDEN_NARROWS_U, expected):
            assert CM.narrow_v(u, v0, half) == pytest.approx(value, abs=1e-3)


def test_strokes_are_one_figure_across_the_pair(strokes):
    for side in SIDES:
        unclipped = [CM.line_curve(k) for k in range(C.COVER_MARK_LINES)] + [CM.steep_curve()]
        inside = MEC._mark_inside(side)
        segments = [(a, b) for points, _ in strokes[side] for a, b in pairwise(points)]
        for points, _ in strokes[side]:
            for p in points:
                assert min(_dist_to_polyline(CM.to_assembled(p, side), line)
                           for line in unclipped) < 1e-6
        # A right-only length limit shortens the steep curve on purpose; check the rest whole.
        whole = unclipped if (side == "left" or C.COVER_MARK_RIGHT_CURVE_LENGTH is None) \
            else unclipped[:-1]
        for line in whole:
            for q in line:
                x, y = CM.to_canonical(q, side)
                if not inside((x, y)):
                    continue
                # Simplification keeps every mark sample within its tolerance of a stroke.
                assert min(_seg_dist((x, y), a, b) for a, b in segments) \
                    <= C.COVER_MARK_SIMPLIFY_TOL+1e-6


def _max_turn_deg(points) -> float:
    worst = 0.0
    for a, b, c in zip(points, points[1:], points[2:]):
        h1, h2 = math.atan2(b[1]-a[1], b[0]-a[0]), math.atan2(c[1]-b[1], c[0]-b[0])
        worst = max(worst, abs((h2-h1+math.pi) % (2*math.pi)-math.pi))
    return math.degrees(worst)


def test_narrows_have_no_kink_where_they_enter_the_right_cover():
    # The fan used to switch on with a slope break at PINCH_U: 3-9 deg in one 0.16 mm step,
    # right at the right cover's entry. Eased (C1), no sample-to-sample turn exceeds 1 deg.
    for k in range(C.COVER_MARK_LINES):
        assert _max_turn_deg(CM.narrows(C.COVER_MARK_CENTER+C.COVER_MARK_SPACING*(k-1))) < 1.0


def test_bow_a_handles_drive_one_smooth_curve_over_both_covers(monkeypatch):
    analytic = CM._analytic_curve()
    handles = CM.default_curve_points()
    monkeypatch.setattr(C, "COVER_MARK_CURVE_POINTS", tuple(handles))
    curve = CM.steep_curve()
    # Starts as the analytic bow, passes through every handle, and has no kink anywhere.
    assert max(_dist_to_polyline(p, analytic) for p in curve[::25]) < 0.15
    assert all(min(math.dist(h, p) for p in curve) < 1e-9 for h in handles)
    assert _max_turn_deg(curve) < 1.0
    # Dragging one handle reshapes the curve, and both covers still cut pieces of it.
    moved = list(handles)
    moved[5] = (moved[5][0]+3.0, moved[5][1]-2.0)
    monkeypatch.setattr(C, "COVER_MARK_CURVE_POINTS", tuple(moved))
    curve = CM.steep_curve()
    for side in SIDES:
        pieces = CM.strokes(side, MEC._mark_inside(side))[-1:]
        for points, _ in pieces:
            assert max(_dist_to_polyline(CM.to_assembled(p, side), curve) for p in points) < 1e-6


def test_line_handles_reshape_one_narrows_line_on_both_covers(monkeypatch):
    formula = CM.line_curve(0)
    handles = CM.default_line_points(0)
    monkeypatch.setattr(C, "COVER_MARK_LINE_POINTS", (tuple(handles), None, None))
    curve = CM.line_curve(0)
    # Starts on the formula with no kink; the other lines keep their formula untouched.
    assert max(_dist_to_polyline(p, formula) for p in curve[::25]) < 0.2
    assert _max_turn_deg(curve) < 1.0
    assert CM.line_curve(1) == CM.narrows(CM.line_v0(1), C.COVER_MARK_LINE_FAN[1])
    moved = list(handles)
    moved[12] = (moved[12][0], moved[12][1]+4.0)
    monkeypatch.setattr(C, "COVER_MARK_LINE_POINTS", (tuple(moved), None, None))
    curve = CM.line_curve(0)
    assert max(_dist_to_polyline(p, formula) for p in curve[::25]) > 1.0
    lines = [curve, CM.line_curve(1), CM.line_curve(2), CM.steep_curve()]
    for side in SIDES:
        for points, _ in CM.strokes(side, MEC._mark_inside(side)):
            assert min(max(_dist_to_polyline(CM.to_assembled(p, side), line) for p in points)
                       for line in lines) < 1e-6


def test_south_line_is_tucked_in_to_an_even_exit_ladder_on_the_right_cover():
    def east_exit(curve):
        runs = CM._inside_runs([CM.to_canonical(p, "right") for p in curve],
                               MEC._mark_inside("right"))
        return max((q for r in runs for q in (r[0], r[-1])), key=lambda q: q[0])[1]

    exits = [east_exit(CM.line_curve(k)) for k in range(C.COVER_MARK_LINES)]
    # The untucked south line ran out ~28 mm below the others; tucked, the ladder is even.
    assert exits[2]-exits[1] == pytest.approx(13.4, abs=0.5)
    assert exits[1]-exits[0] == pytest.approx(13.0, abs=0.5)
    assert east_exit(CM.narrows(CM.line_v0(0))) < exits[0]-10.0
    # The tuck only eases the fan past the pinch, so the left cover's piece is identical.
    left = MEC._mark_inside("left")
    untucked = CM._inside_runs([CM.to_canonical(p, "left") for p in CM.narrows(CM.line_v0(0))], left)
    tucked = CM._inside_runs([CM.to_canonical(p, "left") for p in CM.line_curve(0)], left)
    assert untucked == tucked


def test_right_curve_length_limits_only_the_right_steep_stroke(monkeypatch):
    def steep_length(side: str) -> float:
        runs = CM.strokes(side, MEC._mark_inside(side))[C.COVER_MARK_LINES:]
        return sum(math.dist(a, b) for points, _ in runs for a, b in pairwise(points))

    monkeypatch.setattr(C, "COVER_MARK_RIGHT_CURVE_LENGTH", None)
    full_right, full_left = steep_length("right"), steep_length("left")
    monkeypatch.setattr(C, "COVER_MARK_RIGHT_CURVE_LENGTH", 10.0)
    assert full_right > 12.0
    assert steep_length("right") == pytest.approx(10.0, abs=0.05)
    assert steep_length("left") == pytest.approx(full_left, abs=1e-9)


def test_left_and_right_carry_different_pieces(strokes):
    right = [pt for points, _ in strokes["right"] for pt in points]
    right_segments = [(a, b) for points, _ in strokes["right"] for a, b in pairwise(points)]
    left = [(C.OUTER_WIDTH-pt[0], pt[1]) for points, _ in strokes["left"] for pt in points]
    farthest = max(min(_seg_dist(p, a, b) for a, b in right_segments) for p in left)
    assert right and farthest > 1.0


@pytest.mark.parametrize("side", SIDES)
def test_marked_covers_are_single_valid_solids_with_a_shallow_cut(marked, bare, side):
    assert marked[side].is_valid and len(marked[side].solids()) == 1
    cut = bare[side].volume - marked[side].volume
    assert 2.0 < cut < 80.0


@pytest.mark.parametrize("side", SIDES)
def test_groove_depth_and_roof_thickness_on_the_steep_curve(marked, bare, side):
    candidates = []
    x0, x1, y0, y1 = _bounds()
    for p in CM.steep_curve():
        x, y = CM.to_canonical(p, side)
        if not (x0+4 < x < x1-4 and y0+4 < y < y1-4):
            continue
        if math.dist((x, y), C.pcb_to_case(*C.SW_ENCODER_POS)) < (
                C.COVER_SHAFT_CUTOUT_DIA/2+C.COVER_MARK_QUIET_R):
            continue
        candidates.append((x, y))
    picks = [candidates[len(candidates)*k//4] for k in (1, 2, 3)]
    for x, y in picks:
        roof = MEC._cover_roof_z(y, side)
        if side == "left":
            x = C.OUTER_WIDTH-x
        assert (marked[side] & _probe(x, y, roof-0.15)).volume < 1e-6
        assert (bare[side] & _probe(x, y, roof-0.15)).volume > 0.007
        floor = roof-C.COVER_MARK_DEPTH-0.15
        assert (marked[side] & _probe(x, y, floor)).volume > 0.007
        assert (bare[side] & _probe(x, y, floor)).volume > 0.007


@pytest.mark.parametrize("side", SIDES)
def test_keep_outs_untouched_and_grooves_run_out_through_the_edges(marked, bare, side):
    cut = _sided(bare[side]-marked[side], side)
    z0 = C.PCB_TOP_Z-5.0
    ex, ey, _, _ = MEC._encoder_bbox()
    quiet = Solid.make_cylinder(C.COVER_SHAFT_CUTOUT_DIA/2+C.COVER_MARK_QUIET_R,
                                40.0).translate((ex, ey, z0))
    mcu_x = C.pcb_to_case(*C.MCU_POS)[0]
    north = max(y for _, y in MEC._cover_outer_polygon())
    half = C.COVER_USB_PORT_W/2+1.0
    usb = Solid.make_box(2*half, 10.0, 40.0).translate(
        (mcu_x-half, north-C.COVER_NORTH_WALL-1.0, z0))
    assert (cut & quiet).volume < 1e-6
    assert (cut & usb).volume < 1e-6
    # Old canopy style: grooves break out through the chamfered edges instead of stopping short.
    run = C.COVER_SIDE_CHAMFER_RUN
    band = MEC._face(MEC._cover_polygon(west_inset=run, east_inset=run, north_inset=run,
                                        south_inset=run), C.COVER_CORNER_R)
    box = Solid.make_box(C.OUTER_WIDTH, 200.0, 100.0).translate((-10.0, -50.0, z0))
    edge_band = box-(Pos(0, 0, z0) * extrude(band, amount=40.0))
    assert (cut & edge_band).volume > 0.05
