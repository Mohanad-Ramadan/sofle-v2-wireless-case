"""The canopy roofs' PUZZLE strokes — two CURVES that each cross BOTH halves.

The design: place the two halves as a facing pair and draw two marks across the assembled keyboard.
Each mark crosses both canopies, so each canopy carries two stroke segments — and the four strokes
are really two curves. The mark only completes when both halves are on the desk.

Each mark is a fitted straight BASELINE plus a lateral profile, ``d = A·v³``, with ``v`` measured
from the seam (see THE CURVE, below). The baseline is what the sketch fitted and what everything
else in this module is about; the profile is the restyling, and it is small enough to be switched off
(``PUZZLE_CURVE_A = 0`` gives back the straight mark exactly) and large enough to be the point.

Two consequences fall out for free, and both were requirements:
  • the halves CANNOT look alike. One curve meets each canopy at a different angle, because the
    halves are splayed — so "right must not mirror left" stops being a table of hand-picked numbers
    and becomes arithmetic. Chord dx/dy: line 0 is +1.417 on the left against +0.083 on the right.
    Same curve, different frames.
  • the two halves' pieces are EXACTLY pieces of ONE curve, because both are sampled from one shared
    parameter grid rather than aimed at each other. No tolerance stack, and it holds at any
    separation. Separation only decides WHERE on each roof the mark lands, which is why it is a
    fitted input here and not an alignment constraint.

THE NUMBERS ARE FITTED FROM THE DESIGN SKETCH, NOT INVENTED. The sketch (two rounded rectangles with
four white strokes) was measured by classifying its pixels, recovering each shape's axes by PCA, and
splitting the crossing pair with a small Hough vote. Result: the strokes' page-space angles matched
in pairs to within 0.11°, i.e. the sketch really is two straight lines seen in two splayed frames.
Fitting ONE splay and TWO lines to all four measured strokes lands them within **0.166 mm max /
0.124 mm rms** — so these constants reproduce the drawing to well under a layer line.

Fitting rather than transcribing was deliberate: taken individually the four measured strokes imply
48.6° of splay from one pair and 50.8° from the other, so transcribing all four would bake that 2°
disagreement in and the puzzle would only *nearly* close. One fitted splay plus two fitted lines
makes the halves' agreement exact by construction, and the sketch's own inconsistency shows up
honestly as that 0.166 mm residual instead of hiding as a permanent misalignment.

ONE VALUE IS NOT FROM THE SKETCH — ``PUZZLE_LINE_NUDGE``, which translates line A 3.3 mm to clear the
NW corner — and ``PUZZLE_CURVE_A``, the amplitude, which was chosen by eye. Both are kept as separate
terms rather than folded into the fitted values, precisely so this sentence stays true of everything
else. A translation changes no angle and no relationship between the halves, so the halves' agreement
survives the nudge exactly; the profile is shared by both halves for the same reason.

Every stroke runs out to the roof's edge on the GAP side, so the continuation reads as one mark
rather than as two marks pointing at each other; the RIGHT half's upper stroke additionally breaks
THROUGH the east arris, the switch-column side, which is the one edge actually notched. (The left
half's did too until the amplitude was chosen — see ``PUZZLE_CURVE_A``.) All of those bounds are
passed in (``x0_break``, ``y1_break``, ``x1_north``, ``y0_ramp``) like every other keep-out, so this
module still has no opinion about where the roof ends or which of its edges are chamfered.

This module is PURE PLAN GEOMETRY and imports only ``constants``. It must never import ``canopy`` —
the direction is canopy → canopy_puzzle. The safe region is passed in, so the module has no opinion
about the roof's keep-outs; ``canopy`` owns those.

Assembled frame: origin at the LEFT half's own case origin, +x right, +y away from the user.
  left  half = its canopy coords MIRRORED (x → OUTER_WIDTH − x), then rotated by +splay_half
  right half = its canopy coords,                                then rotated by −splay_half,
                                                                 then translated by RIGHT_OFFSET
"""
from __future__ import annotations
import math

from . import constants as C

# A stroke is a POLYLINE, ordered along its own run — two points while the marks are straight, many
# once they curve. Everything downstream (the cutter, the wall crossings, the tests) reads it as a
# sequence of points rather than a pair, so the shape of the mark and the plumbing that carries it are
# independent.
Stroke = tuple[tuple[float, float], ...]

# ---------------------------------------------------------------------------
# Fitted from the sketch — see the module docstring for the method and the residual.
# ---------------------------------------------------------------------------
PUZZLE_SPLAY_HALF_DEG = -24.671392          # per half; total splay 49.34° between the two halves
PUZZLE_RIGHT_OFFSET = (212.081635, -84.171123)   # right half's placement relative to the left
# Each line as (angle of its NORMAL in degrees, signed offset): the line is {q : n·q = offset} with
# n = (cos θ, −sin θ). Stored this way because it is what the fit solves for, and because a normal
# form has no singularity for near-vertical lines the way a slope does.
PUZZLE_LINES = ((-36.124941, 157.132546),        # line A — 53.9° from horizontal, assembled
                (87.469761, -10.623664))         # line B — 2.5° from horizontal, nearly level
PUZZLE_SKETCH_RESIDUAL = 0.1663                  # mm; worst distance from a sketched stroke to its
#                                                  fitted line. Recorded so a future edit can tell
#                                                  whether it improved or degraded the fit.

# ---------------------------------------------------------------------------
# The ONE deliberate departure from the fit. Kept separate from PUZZLE_LINES on purpose: everything
# above reproduces the drawing, this does not, and the two must not be confused by a later reader.
# ---------------------------------------------------------------------------
# Line A is TRANSLATED 3.3 mm perpendicular to itself. As fitted it left the right roof 1.3 mm from
# the NW corner, where the west shoulder facet, the north-top chamfer and the corner round already
# meet — four features converging inside ~2 mm, which read as damage rather than as a mark. Moved
# east, the stroke leaves cleanly through the straight part of the north edge instead.
#
# It is a TRANSLATION, so the angle, the splay and the exact collinearity are all untouched (spread
# stays ~1e-14 mm): both halves' segments move together because they are still segments of one line.
# What it costs is placement fidelity — 3.3 mm is ~20x PUZZLE_SKETCH_RESIDUAL, so line A no longer
# lands where the drawing puts it. That is the trade, stated in one number that can be zeroed.
#
# The value is bounded on BOTH sides, and neither bound is taste. Measured where the stroke crosses
# the north WALL (canopy.puzzle_north_crossings) — not at its endpoint, which sits a break's-worth
# beyond and, because the stroke is tilted, 0.2 mm west per mm of that overshoot. Every number below
# is re-measured on the CURVED mark at CANOPY_PUZZLE_W = 1.0 and WITH the crossing tilt: line A meets
# that wall at 78.6°, so the groove's footprint along the wall is (w/2)/sin θ = 0.51 mm per side
# rather than 0.50 — a correction the window itself cannot make, and one that was being spent
# silently while the groove was 1.6 wide.
#
# The curve barely moves this, and that is worth knowing rather than assuming: line A leaves the part
# essentially AT THE SEAM (t −76.9 against the seam's −75.9), where the odd-cubic profile passes
# through zero, so the exit lands within 0.6 µm of where the straight baseline put it and the
# amplitude cannot spend the corner clearance however bold the mark gets out on the roof.
#   ≥ 2.65   the whole groove width must leave through the STRAIGHT north edge — the corner arc is
#            tangent to the wall at x = CANOPY_WEST_OUTER_X + CANOPY_CORNER_R. Below this ``canopy``
#            refuses the north break outright and the stroke stops inboard instead, which is visible
#            and safe rather than silent. (2.94 at the old 1.6 mm width.)
#   ≤ 4.42   past this the crossing comes within CANOPY_PUZZLE_POCKET_GAP of the USB pocket. (4.16.)
#   (the old ≈ 4.6 ceiling — where the LEFT half's line 0 stops breaking the east arris — is spent:
#    PUZZLE_CURVE_A = 4.75 has already taken that break, so this bound no longer binds anything.)
# Scanned at 0.1: the break is open from 2.7 to 4.4 and refused either side of that. At 3.3 the
# margins are corner 0.66 mm and pocket 2.17 mm (1.17 beyond the required gap) — the narrower groove
# bought most of the corner clearance. The window's own middle is 3.54, so there is room to re-centre
# if the corner ever wants more air.
PUZZLE_LINE_NUDGE = (3.3, 0.0)                   # mm, added to each line's fitted offset


def line_offset(index: int) -> float:
    """Line ``index``'s offset AS BUILT — the fitted value plus its nudge, if any."""
    return PUZZLE_LINES[index][1] + PUZZLE_LINE_NUDGE[index]


# ---------------------------------------------------------------------------
# THE CURVE. The marks are not straight any more; each one is its line plus a lateral profile, and
# the profile is a function of position ALONG THE LINE in the assembled frame. That is the whole
# design, and it is what keeps every property the straight version had:
#
#   • both halves sample ONE function of one parameter, so the two pieces of a mark are pieces of one
#     curve rather than two curves aimed at each other. The residual is machine noise (~1e-14 mm), the
#     same as the old collinearity, and ``assembled_offcurve_spread`` measures it.
#   • the fitted line is still there, underneath, as the curve's baseline — so "fitted from the
#     sketch" stays a true statement about the layout, and the departure has a name and a size.
#   • the profile is an ODD CUBIC about the SEAM, so it is zero AND flat AND has zero curvature where
#     the two halves hand over. A misplaced pair therefore costs exactly what it cost when the marks
#     were straight; the curvature is spent out on the roofs, where there is nothing to compare it
#     against. Putting the bend anywhere else would add a visible kink at the join to the step that
#     misplacement already causes.
# ---------------------------------------------------------------------------
# THE AMPLITUDE IS A CHOSEN NUMBER, and the only one in this module that is not fitted or derived —
# picked by eye in a browser lab against the real roof outlines, from a family of six. 0.0 IS the
# straight mark, so the whole curve can be switched off in one edit and the old geometry comes back
# exactly (``_drop_collinear`` then returns two points per stroke, not fifty).
#
# 7 mm is past the point where every old invariant survives, and it was chosen ANYWAY, knowingly
# (was 4.75, now 7 — increased to clear the slide-switch scoop on the right half with a fair gap).
# Measured on the real geometry at 7 parallel — min radius 38.6 / 39.3 mm, still >25 mm, so the mark
# reads as drawn but tighter:
#
#   left  A  25.8 mm   y 103.0..118.5   stops in open roof — NO east notch   <- a loss, accepted
#   left  B  24.0 mm   y  78.8.. 86.2   crosses the ramp
#   right A  45.7 mm   y  78.2..122.5   starts 2.7 mm north of the slide scoop (was 59.6, ran whole ramp)
#   right B  34.1 mm   y  87.6..108.5   breaks the east arris
#
# The two losses, both real and both deliberate:
#   • the east arris is notched ONCE IN THE PAIR (right half only) instead of once per half. The bow
#     lifts the left half's line A off the east wall — the same failure ``PUZZLE_LINE_NUDGE``'s upper
#     bound guards against, arrived at from the other direction (short now 4.7 mm at 7, was 3.2 at 4.75).
#   • right A now starts at y 78.2, 2.7 mm north of the slide scoop top (was clipped by the WEST edge
#     0.8 mm short of the ramp foot at 4.75). It still crosses the ramp (78.2 < 81.56) and exits north,
#     so the ramp-crossing cutter is still justified; it is just no longer the foot terminal the lab drew.
#
# The alternative was A ≈ 2.10, which keeps both notches AND lands right A exactly on the foot at
# 58.8 (min radius 86 mm) — every invariant intact, at a peak departure of 2.1 mm instead of 7,
# i.e. a bow you have to look for. Offered and declined: the mark is the point. Anyone re-tuning this
# should know that 2.10 is where "nothing is given up" ends, not that 7 is a safe default.
PUZZLE_CURVE_A = 7       # mm; the profile's value at |v| = 1 — the whole family's peak departure
#                             from the baseline inside the fitted span. 0.0 IS the straight mark.
PUZZLE_CURVE_HANDS = (+1, +1)   # which way each line bends. Same sign = the pair reads as parallel
#                                 curves; opposite = they bow away from each other. Mirrored (−1, −1)
#                                 keeps both east notches at 4.75 but pulls right A off the ramp
#                                 entirely (it stops at y 83.1), which costs the ramp crossing the
#                                 normal-offset cutter exists for. Parallel was chosen with that
#                                 trade on the table.
PUZZLE_CURVE_PAD = 34.0     # mm of t sampled beyond the fitted span, so every break has curve to
#                             clip against; the extension is straight (see ``curve_lateral``).
PUZZLE_CHORD_SAG = 0.02     # mm; the most a sampled chord may deviate from the analytic cubic. A
#                             tenth of a layer line, an eighth of PUZZLE_SKETCH_RESIDUAL. Unlike
#                             CANOPY_RAMP_SAMPLES this is a FLOOR with no cliff above it: refining it
#                             adds planar faces linearly and densifies no spline. Do not confuse them.
PUZZLE_CURVE_MIN_R = 25.0   # mm; below this a 1 mm groove stops reading as a drawn line and reads as
#                             a hook. Asserted, not hoped for.

# The parameterisation, and it is load-bearing. ``t`` is arclength along the baseline in the assembled
# frame (t = q·u_hat, side-free by construction); ``u`` normalises it over the span the two halves'
# marks actually occupy, and ``u_seam`` is where the gap between the halves falls along it.
#
# THE SPAN COMES FROM THE SHIPPED STRAIGHT LAYOUT — the strokes as ``straight_strokes`` cuts them,
# breaks and trims included — and NOT from the raw safe-region chords. That is not a detail: derived
# from the region chords instead, line A's span comes out 89.5 mm with the seam at u 0.72, and the
# same amplitude then produces a mark whose lateral departure is 0.4 mm, i.e. visually straight. The
# numbers below are pinned so the shape cannot drift, and ``span_from_straight`` re-derives them so
# the pin cannot become a fiction.
# The values below are for the layout AS IT SHIPS — 1.0 mm groove, so 1.0 mm breaks. They are
# width-sensitive, and not trivially: every break is one groove width long, so narrowing the groove
# from 1.6 pulled all four terminals in by 0.6 mm and moved the span with them (line A: −107.436 →
# −107.741, u_seam 0.507 → 0.516). At A = 4.75 that is 1.3 mm of lateral difference — small, but not
# nothing, which is exactly why this is re-derived and asserted rather than transcribed once.
PUZZLE_CURVE_SPAN = {0: (-107.741015, -45.965048, 0.515849),   # (t_lo, t_hi, u_seam)
                     1: (150.930533, 204.245456, 0.395154)}


def _line_frame(index: int) -> tuple[tuple[float, float], tuple[float, float], float]:
    """``(n, u_hat, offset)`` for a line in the ASSEMBLED frame.

    ``n`` is the stored normal, ``u_hat`` the unit direction along the line, and ``t = q·u_hat`` is
    therefore a canonical parameter that belongs to the LINE and not to either half — which is what
    lets both halves sample one profile."""
    th = math.radians(PUZZLE_LINES[index][0])
    return (math.cos(th), -math.sin(th)), (math.sin(th), math.cos(th)), line_offset(index)


def curve_t(index: int, q: tuple[float, float]) -> float:
    """An ASSEMBLED point's position along line ``index``."""
    _, u, _ = _line_frame(index)
    return q[0] * u[0] + q[1] * u[1]


def curve_lateral(index: int, t: float) -> float:
    """The profile: ``A·v³`` inside the fitted span, a STRAIGHT run-out beyond it.

    ``v`` is measured from the seam and scaled so it reaches ±1 at the span's far end, which is what
    makes ``A`` the mark's peak departure rather than an arbitrary coefficient.

    Outside the span the profile continues along its own tangent — C1, not clamped. A clamp would put
    a slope discontinuity within a break's-length of the terminals that run off the arrises, i.e. in
    the one place the eye follows the mark off the part."""
    t_lo, t_hi, u_seam = PUZZLE_CURVE_SPAN[index]
    u = (t - t_lo) / (t_hi - t_lo)
    h = max(u_seam, 1.0 - u_seam)

    def core(uu: float) -> float:
        v = (uu - u_seam) / h
        return PUZZLE_CURVE_HANDS[index] * PUZZLE_CURVE_A * v ** 3

    if 0.0 <= u <= 1.0:
        return core(u)
    u_c = 0.0 if u < 0.0 else 1.0
    step = 1e-4 if u < 0.0 else -1e-4
    slope = (core(u_c + step) - core(u_c)) / step
    return core(u_c) + slope * (u - u_c)


def curve_point(index: int, t: float) -> tuple[float, float]:
    """The curve itself, in the assembled frame: baseline plus profile, along the line's own normal."""
    n, u, off = _line_frame(index)
    d = off + curve_lateral(index, t)
    return (d * n[0] + t * u[0], d * n[1] + t * u[1])


def curve_min_radius(index: int) -> float:
    """Smallest radius of curvature over the fitted span. Straight (``inf``) at ``PUZZLE_CURVE_A`` 0."""
    t_lo, t_hi, _ = PUZZLE_CURVE_SPAN[index]
    worst = float("inf")
    for k in range(401):
        t = t_lo + (t_hi - t_lo) * k / 400
        e = (t_hi - t_lo) / 2000
        d0 = curve_lateral(index, t - e)
        d1 = curve_lateral(index, t)
        d2 = curve_lateral(index, t + e)
        first = (d2 - d0) / (2 * e)
        second = (d2 - 2 * d1 + d0) / (e * e)
        if abs(second) > 1e-12:
            worst = min(worst, (1 + first * first) ** 1.5 / abs(second))
    return worst


def curve_samples(index: int) -> list[float]:
    """The SHARED t grid, padded past the span so the breaks have curve to clip against.

    Shared is the point: both halves read the same t values, so every vertex of every stroke is a
    vertex of one polyline and the two pieces of a mark meet exactly, not just closely. The step comes
    from the chord-sag budget on the curve's own tightest radius (``chord = √(8·R·sag)``), so a
    flatter line is sampled more coarsely and neither is sampled by a number someone picked."""
    t_lo, t_hi, _ = PUZZLE_CURVE_SPAN[index]
    r = curve_min_radius(index)
    step = 2.0 if r == float("inf") else min(2.0, math.sqrt(8 * r * PUZZLE_CHORD_SAG))
    lo, hi = t_lo - PUZZLE_CURVE_PAD, t_hi + PUZZLE_CURVE_PAD
    n = max(2, math.ceil((hi - lo) / step) + 1)
    return [lo + (hi - lo) * k / (n - 1) for k in range(n)]


def span_from_straight(index: int, straight: dict[str, list[Stroke]]) -> tuple[float, float, float]:
    """Re-derive ``PUZZLE_CURVE_SPAN[index]`` from the shipped STRAIGHT strokes of both halves.

    The hull of the two halves' extents along the line gives the span; the midpoint of the interval
    BETWEEN them gives the seam. Both halves must appear, and their extents must be disjoint — if they
    overlap there is no gap, and therefore no seam to anchor the profile's inflection to."""
    ends = {}
    for side, segs in straight.items():
        ts = [curve_t(index, to_assembled(p, side)) for p in (segs[index][0], segs[index][-1])]
        ends[side] = (min(ts), max(ts))
    (a_lo, a_hi), (b_lo, b_hi) = ends["left"], ends["right"]
    t_lo, t_hi = min(a_lo, b_lo), max(a_hi, b_hi)
    gap_lo, gap_hi = max(a_lo, b_lo), min(a_hi, b_hi)
    assert gap_lo >= gap_hi - 1e-6, (
        f"line {index}: the halves' extents overlap along the line — there is no gap, so no seam"
    )
    return (t_lo, t_hi, ((gap_lo + gap_hi) / 2 - t_lo) / (t_hi - t_lo))

# How much of its own chord across the roof each stroke covers — i.e. where it STOPS, which the
# line fit above says nothing about. Measured from the same sketch by the same kind of method: the
# white stroke pixels were split into two lines by RANSAC and each stroke's extent compared with its
# line's chord clipped against that shape's oriented box. A ratio measured ALONG a line is invariant
# under any affine map, so this needs no page→mm transform and is immune to the sketch rectangles'
# aspect (2.43) differing from the roof strip's (2.60) — which is exactly why it is stated as a
# fraction and not as a length in mm.
#
# All four measured: left line 0 = 1.007, left line 1 = 0.666, right line 0 = 0.502,
# right line 1 = 1.006. So the sketch gives each half ONE stroke that spans its roof edge to edge
# and one that stops — and the halves differ in WHICH, which is the same splay-driven asymmetry the
# angles have. The two below 1.0 are applied; the two at ~1.0 are simply the absence of a trim.
#
# Anchored at the NORTH end: that is the end the sketch's stroke has on the shape's edge, so the
# trim takes the free terminal back — south on the right half's line 0, east on the left half's
# line 1 (on that stroke the north end IS the west one).
PUZZLE_STROKE_COVER = {("right", 0): 0.502, ("left", 1): 0.666}


def _rot(p: tuple[float, float], th: float) -> tuple[float, float]:
    return (p[0] * math.cos(th) - p[1] * math.sin(th),
            p[0] * math.sin(th) + p[1] * math.cos(th))


def to_assembled(pt: tuple[float, float], side: str) -> tuple[float, float]:
    """A point in that half's UN-MIRRORED canopy coords → the assembled frame.

    The left half is mirrored first because ``case.build_top_part`` mirrors it; the canopy is always
    modelled un-mirrored, so anything reasoning about the assembled pair has to apply that mirror
    itself."""
    b = math.radians(PUZZLE_SPLAY_HALF_DEG)
    if side == "left":
        return _rot((C.OUTER_WIDTH - pt[0], pt[1]), +b)
    q = _rot(pt, -b)
    return (q[0] + PUZZLE_RIGHT_OFFSET[0], q[1] + PUZZLE_RIGHT_OFFSET[1])


def to_canopy(pt: tuple[float, float], side: str) -> tuple[float, float]:
    """The exact inverse of ``to_assembled`` — an assembled point in that half's own canopy coords.

    This is the direction the curve travels: the mark is drawn once for the assembled keyboard and
    then pulled back into each half's frame to be cut, which is why neither half owns a shape."""
    b = math.radians(PUZZLE_SPLAY_HALF_DEG)
    if side == "left":
        q = _rot(pt, -b)
        return (C.OUTER_WIDTH - q[0], q[1])
    q = (pt[0] - PUZZLE_RIGHT_OFFSET[0], pt[1] - PUZZLE_RIGHT_OFFSET[1])
    return _rot(q, +b)


def line_in_canopy(side: str, index: int) -> tuple[float, float, float]:
    """Line ``index`` pulled back into a half's UN-MIRRORED canopy coords, as ``(a, b, c)`` meaning
    ``a·x + b·y = c``.

    This is the whole "equation": one assembled-frame line, expressed in each half's own frame. The
    two halves' strokes are then segments of the same line by construction, which is what makes the
    puzzle close exactly instead of approximately. It reads the AS-BUILT offset (``line_offset``), so
    a nudge lands on both halves through the same equation and cannot desynchronise them."""
    ang, off = PUZZLE_LINES[index][0], line_offset(index)
    th = math.radians(ang)
    n = (math.cos(th), -math.sin(th))
    b = math.radians(PUZZLE_SPLAY_HALF_DEG)
    sgn = +1.0 if side == "left" else -1.0
    # world = R(sgn·b)·(mirror? p) + T  ⇒  (Rᵀn)·(mirror? p) = off − n·T
    nr = (n[0] * math.cos(sgn * b) + n[1] * math.sin(sgn * b),
          -n[0] * math.sin(sgn * b) + n[1] * math.cos(sgn * b))
    if side == "left":
        rhs = off
        # nr·(W − x, y) = rhs  ⇒  −nr₀·x + nr₁·y = rhs − nr₀·W
        return (-nr[0], nr[1], rhs - nr[0] * C.OUTER_WIDTH)
    rhs = off - (n[0] * PUZZLE_RIGHT_OFFSET[0] + n[1] * PUZZLE_RIGHT_OFFSET[1])
    return (nr[0], nr[1], rhs)


def _clip_to_rect(a: float, b: float, c: float, x0: float, x1: float, y0: float,
                  y1: float) -> list[tuple[float, float]]:
    """Where ``a·x + b·y = c`` enters and leaves the rectangle. Empty if it misses."""
    hits: list[tuple[float, float]] = []
    if abs(b) > 1e-12:
        for xv in (x0, x1):
            yv = (c - a * xv) / b
            if y0 - 1e-9 <= yv <= y1 + 1e-9:
                hits.append((xv, yv))
    if abs(a) > 1e-12:
        for yv in (y0, y1):
            xv = (c - b * yv) / a
            if x0 - 1e-9 <= xv <= x1 + 1e-9:
                hits.append((xv, yv))
    uniq: list[tuple[float, float]] = []
    for h in hits:
        if not any(math.hypot(h[0] - u[0], h[1] - u[1]) < 1e-6 for u in uniq):
            uniq.append(h)
    return sorted(uniq, key=lambda p: p[1])


def upper_index(side: str, x0: float, x1: float, y0: float, y1: float) -> int:
    """Which stroke is the UPPER one on a roof, decided on the SAFE-REGION chords.

    Exported so callers and tests ask the same question the cutter asked. It has to be answered
    before any break or trim: breaks lengthen a stroke and trims shorten it, so a midpoint taken
    from the finished segments can name the other stroke — which would silently move the east break
    to the wrong one."""
    return north_index([(pts[0], pts[-1]) for pts in
                        (_clip_to_rect(*line_in_canopy(side, i), x0, x1, y0, y1)
                         for i in range(len(PUZZLE_LINES)))])


def north_index(segs: list[Stroke]) -> int:
    """Which stroke is the UPPER one on this roof — the northernmost by MEAN vertex Y.

    Derived, not tabulated: the two halves are splayed, so the same assembled line is the upper one
    on one roof and the lower one on the other (today: line 0 on the left, line 1 on the right). A
    hand-written per-side index would silently point at the wrong stroke the moment the splay or the
    separation is re-fitted.

    Mean of the vertices rather than the midpoint of the chord: on a curved stroke the chord ignores
    the bow, and the two can disagree by over a millimetre. For a two-point stroke the mean IS the
    midpoint, so nothing about the straight answer changes."""
    return max(range(len(segs)), key=lambda i: sum(p[1] for p in segs[i]) / len(segs[i]))


def _clip_seg(p: tuple[float, float], q: tuple[float, float],
              box: tuple[float, float, float, float]
              ) -> tuple[tuple[float, float], tuple[float, float]] | None:
    """The part of segment ``p→q`` inside ``box``, or None. Liang–Barsky, in the obvious form."""
    x0, x1, y0, y1 = box
    t_lo, t_hi = 0.0, 1.0
    for c, d, lo, hi in ((p[0], q[0] - p[0], x0, x1), (p[1], q[1] - p[1], y0, y1)):
        if abs(d) < 1e-12:
            if c < lo - 1e-9 or c > hi + 1e-9:
                return None
            continue
        ta, tb = (lo - c) / d, (hi - c) / d
        t_lo, t_hi = max(t_lo, min(ta, tb)), min(t_hi, max(ta, tb))
        if t_lo > t_hi:
            return None
    at = lambda t: (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)
    return at(t_lo), at(t_hi)


def _clip_poly_to_rect(pts: list[tuple[float, float]], x0: float, x1: float, y0: float, y1: float
                       ) -> list[list[tuple[float, float]]]:
    """Every maximal RUN of a polyline inside the rectangle, each capped at the exact boundary.

    A list of runs, not one run, because a curve can leave the region and come back where a straight
    chord could not. Callers are expected to refuse that rather than pick one — see ``strokes``."""
    box = (x0, x1, y0, y1)
    runs: list[list[tuple[float, float]]] = []
    cur: list[tuple[float, float]] | None = None
    for p, q in zip(pts, pts[1:]):
        piece = _clip_seg(p, q, box)
        if piece is None:
            cur = None
            continue
        a, b = piece
        if cur is not None and math.hypot(a[0] - cur[-1][0], a[1] - cur[-1][1]) < 1e-9:
            cur.append(b)
        else:
            cur = [a, b]
            runs.append(cur)
    return [_dedup_pts(r) for r in runs if len(_dedup_pts(r)) >= 2]


def _dedup_pts(pts: list[tuple[float, float]]) -> list[tuple[float, float]]:
    out = [pts[0]]
    for p in pts[1:]:
        if math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > 1e-9:
            out.append(p)
    return out


def _drop_collinear(pts: list[tuple[float, float]], tol: float = 1e-9
                    ) -> list[tuple[float, float]]:
    """Drop stations that sit on the chord between their neighbours.

    A straight mark then comes back as exactly two points, whatever the sampling was, so
    ``PUZZLE_CURVE_A = 0`` reproduces the old geometry rather than merely resembling it — and the
    cutter is never handed a polygon with fifty collinear vertices to make coplanar faces out of."""
    if len(pts) <= 2:
        return list(pts)
    out = [pts[0]]
    for a, b, c in zip(pts, pts[1:], pts[2:]):
        ux, uy = c[0] - a[0], c[1] - a[1]
        L = math.hypot(ux, uy)
        if L < 1e-12 or abs((b[0] - a[0]) * uy - (b[1] - a[1]) * ux) / L > tol:
            out.append(b)
    out.append(pts[-1])
    return out


def curve_in_canopy(side: str, index: int) -> list[tuple[float, float]]:
    """The whole padded curve for line ``index``, in one half's UN-MIRRORED canopy coords.

    Sampled on the SHARED t grid and then pulled back through ``to_canopy``, so the two halves'
    strokes are literally cut from the same list of assembled points."""
    return [to_canopy(curve_point(index, t), side) for t in curve_samples(index)]


def strokes(side: str, x0: float, x1: float, y0: float, y1: float,
            x1_north: float | None = None, x0_break: float | None = None,
            y1_break: float | None = None, y0_ramp: float | None = None) -> list[Stroke]:
    """Both strokes for a half as POLYLINES, clipped to the safe rectangle, ordered south → north.

    The curve is defined once for the assembled pair and simply STOPS where the roof stops being safe
    to cut — the same rule the straight version used, and the reason the continuation still reads as
    one mark rather than as two marks that resemble each other.

    ``x1_north`` overrides the EAST bound for the upper stroke alone (see ``north_index``): pass a
    value past ``CANOPY_EAST_X`` and that one stroke breaks the east arris on purpose. ``x0_break``
    and ``y1_break`` are the west and north run-outs. ``y0_ramp`` lowers the SOUTH bound to the ramp
    foot, which is safe only because the cutter's depth reaches zero there (``puzzle_depth_at``) —
    the keep-out in ``y0`` exists to stop a fixed-depth groove spilling onto the cover, and a groove
    that has already faded to nothing cannot spill. Every one of them only moves where the curve is
    CLIPPED, never where it runs, so both halves' strokes stay pieces of the same curve no matter
    which breaks are open — and in particular none of them may feed back into ``PUZZLE_CURVE_SPAN``,
    which is pinned to the straight layout WITHOUT them.

    A stroke that enters the region more than once is REFUSED, not tidied: the design's claim is one
    mark per line per half, and silently keeping the longest run would leave a fifth mark on the roof
    with every test still green. It cannot happen while the seam — and with it the profile's
    inflection — sits inside the gap, because each half's piece is then convex."""
    n = upper_index(side, x0, x1, y0, y1)
    out: list[Stroke] = []
    for i in range(len(PUZZLE_LINES)):
        poly = curve_in_canopy(side, i)
        xa = x0 if x0_break is None else x0_break
        xb = x1_north if (i == n and x1_north is not None) else x1

        ya = y0 if y0_ramp is None else y0_ramp

        # The north break is simply the north bound when it is given. It used to be gated a second
        # time in here — let out only if the gap-side terminal was the one the keep-out had stopped —
        # and on a curve that gate reads the wrong end: the westmost terminal of a bowed mark can be
        # its SOUTH one, so the stroke heading for the NW corner would be refused the break and stop
        # in open roof instead. The gate that matters is the one in ``canopy``, which checks where the
        # stroke actually crosses the wall and re-clips BOTH strokes without the break if the exit is
        # not in the safe window. One gate, on the thing being protected.
        runs = _clip_poly_to_rect(poly, xa, xb, ya, y1 if y1_break is None else y1_break)
        assert runs, (
            f"{side}: puzzle line {i} misses the safe region entirely — the fitted layout no longer "
            f"puts it on this roof"
        )
        assert len(runs) == 1, (
            f"{side}: puzzle line {i} enters the region {len(runs)} times — PUZZLE_CURVE_A has bent "
            f"it back onto the roof, so 'one mark per line per half' is no longer true"
        )
        run = _drop_collinear(runs[0])
        out.append(tuple(run if run[0][1] <= run[-1][1] else run[::-1]))
    return out


def assembled_polyline(index: int) -> list[tuple[float, float]]:
    """THE mark for line ``index``, once, in the assembled frame. Both halves cut pieces of this."""
    return [curve_point(index, t) for t in curve_samples(index)]


def _dist_to_polyline(q: tuple[float, float], poly: list[tuple[float, float]]) -> float:
    best = float("inf")
    for a, b in zip(poly, poly[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 < 1e-18 else max(0.0, min(1.0, ((q[0] - a[0]) * dx + (q[1] - a[1]) * dy) / L2))
        best = min(best, math.hypot(q[0] - (a[0] + t * dx), q[1] - (a[1] + t * dy)))
    return best


def assembled_offcurve_spread(side_strokes: dict[str, list[Stroke]]) -> list[float]:
    """For each line, how far the FURTHEST vertex of either half sits off the ONE assembled polyline.

    This is what exact collinearity becomes once the mark is curved, and it is the same kind of
    statement: both halves' vertices lie on ONE object to machine precision (~1e-14 mm), because they
    are sampled from one shared t grid and clipped against it — not aimed at each other.

    Measured against the POLYLINE, not the analytic cubic, and the distinction is the honest one: the
    polyline is what gets cut, and a clipped terminal lands on a chord by construction, so measuring
    against the cubic would report the sampling budget (~0.01 mm) and call it a continuity error. The
    sampling is a separate claim with its own number — see ``polyline_sag``."""
    out = []
    for i in range(len(PUZZLE_LINES)):
        poly = assembled_polyline(i)
        worst = 0.0
        for side in ("left", "right"):
            for p in side_strokes[side][i]:
                worst = max(worst, _dist_to_polyline(to_assembled(p, side), poly))
        out.append(worst)
    return out


def polyline_sag(index: int) -> float:
    """How far the sampled polyline departs from the analytic cubic, at the worst chord midpoint.

    The other half of the continuity story: ``assembled_offcurve_spread`` says the two halves cut one
    polyline, this says that polyline is the curve. Budgeted by ``PUZZLE_CHORD_SAG``."""
    ts = curve_samples(index)
    worst = 0.0
    for a, b in zip(ts, ts[1:]):
        mid = (a + b) / 2
        pa, pb, pm = curve_point(index, a), curve_point(index, b), curve_point(index, mid)
        worst = max(worst, _dist_to_polyline(pm, [pa, pb]))
    return worst


def straight_strokes(side: str, x0: float, x1: float, y0: float, y1: float,
                     x1_north: float | None = None, x0_break: float | None = None,
                     y1_break: float | None = None
                     ) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """The FITTED STRAIGHT layout — no longer what gets cut, and kept for one reason.

    ``PUZZLE_CURVE_SPAN`` is derived from this: the span the marks occupy and where the gap falls
    along them. So this function has to keep every term the sketch had, ``PUZZLE_STROKE_COVER``
    included, even though the trims themselves are not cut any more — the parameterisation is pinned
    to the layout as the sketch fitted it, and re-deriving it from anything else changes the shape of
    the curve. ``span_from_straight`` is the check that the pin still matches.

    It is also the baseline the curve is measured against, which is what keeps "fitted from the
    sketch" a true statement about the layout rather than a historical note.

    Clipping is what keeps the marks off the shoulder facet and the USB pocket's roof: the lines are
    defined for the assembled keyboard and simply STOP where the roof stops being safe to cut.

    ``x1_north`` overrides the EAST bound for the upper stroke alone (see ``north_index``). It is how
    that one stroke runs into the wall bordering the switch columns instead of dying short of it —
    pass a value past ``CANOPY_EAST_X`` and the stroke breaks the east arris on purpose. The lower
    stroke keeps the inset bound, so exactly one terminal per half is open and the rest stay inboard.
    The override only moves an ENDPOINT along the line; both halves' strokes remain segments of the
    same assembled line, so collinearity is untouched by it.

    ``PUZZLE_STROKE_COVER`` then pulls a stroke's free SOUTH terminal back to a measured fraction of
    its chord, which is how the right half's line 0 stops at mid-roof instead of running the whole
    way. Same argument: it slides an endpoint along the line, so the two halves still read as one
    line across the gap — a stroke may stop early, but it may not stop somewhere else."""
    out = []
    for i in range(len(PUZZLE_LINES)):
        pts = _clip_to_rect(*line_in_canopy(side, i), x0, x1, y0, y1)
        assert len(pts) >= 2, (
            f"{side}: puzzle line {i} misses the safe region entirely — the fitted layout no longer "
            f"puts it on this roof"
        )
        out.append((pts[0], pts[-1]))
    # Decided on the SAFE-REGION chords, before any break or trim — a stroke's identity must not
    # depend on how far it happens to run.
    n = upper_index(side, x0, x1, y0, y1)

    for i in range(len(out)):
        xa = x0 if x0_break is None else x0_break
        xb = x1_north if (i == n and x1_north is not None) else x1
        pts = _clip_to_rect(*line_in_canopy(side, i), xa, xb, y0, y1)
        assert len(pts) >= 2, f"{side}: puzzle line {i} misses the region once broken out to {xa}"
        # A stroke whose gap-side end is held by the NORTH keep-out never reaches the west wall — it
        # is heading for the NW corner. Let that one out through the north wall instead, so both
        # halves' segments of a line leave into the gap rather than one of them stopping in open
        # roof. Derived from where the clip actually landed, not from a per-side table.
        west = min(pts, key=lambda p: p[0])
        if y1_break is not None and abs(west[1] - y1) < 1e-9 and west[0] > xa + 1e-9:
            pts = _clip_to_rect(*line_in_canopy(side, i), xa, xb, y0, y1_break)
            assert len(pts) >= 2, f"{side}: puzzle line {i} misses the roof once let out north"
        out[i] = (pts[0], pts[-1])

    # Trim LAST, and against the broken-out chord: the coverage fraction is "how much of the roof
    # this stroke crosses", so it is measured on the stroke's real full run. Anchored at the north
    # end — the end the sketch has on the shape's edge — so the trim can only pull the free south
    # terminal back.
    for i in range(len(out)):
        f = PUZZLE_STROKE_COVER.get((side, i), 1.0)
        if f < 1.0:
            (sx, sy), (nx, ny) = out[i]                      # ordered south → north
            out[i] = ((nx + (sx - nx) * f, ny + (sy - ny) * f), (nx, ny))
    return out


# ``assembled_offline_spread`` — the straight mark's collinearity measure, an SVD of the four
# endpoints — lived here and is gone with the straight mark. Its successor is
# ``assembled_offcurve_spread``: same claim, same magnitude (~1e-14 mm), against the curve the
# halves are actually cut from. Measuring the curved strokes for straightness would only ever have
# reported the amplitude.


# %%
if __name__ == "__main__":
    for s in ("left", "right"):
        print(s)
        for i, seg in enumerate(strokes(s, 14.1, 32.2, 60.3, 118.5, x1_north=36.2)):
            (ax, ay), (bx, by) = seg[0], seg[-1]
            length = sum(math.dist(a, b) for a, b in zip(seg, seg[1:]))
            print(f"  line {i}: ({ax:6.2f},{ay:7.2f}) -> ({bx:6.2f},{by:7.2f})   "
                  f"{len(seg):3d} pts  {length:5.1f} mm  chord dx/dy {(bx - ax) / (by - ay):+7.3f}")
