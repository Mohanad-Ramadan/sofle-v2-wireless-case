"""The canopy roofs' PUZZLE strokes — two straight lines that each cross BOTH halves.

The design: place the two halves as a facing pair and draw two straight lines across the assembled
keyboard. Each line crosses both canopies, so each canopy carries two stroke segments — and the four
strokes are really two lines. The mark only completes when both halves are on the desk.

Two consequences fall out for free, and both were requirements:
  • the halves CANNOT look alike. One line meets each canopy at a different angle, because the
    halves are splayed — so "right must not mirror left" stops being a table of hand-picked numbers
    and becomes arithmetic. On the right half one stroke even runs nearly lengthwise (dx/dy ≈ −0.20)
    while its partner on the left runs across (dx/dy ≈ +1.79). Same line, different frames.
  • the strokes are EXACTLY collinear across the gap, because they are cut from one line rather than
    aimed at each other. No tolerance stack, and it holds at any separation: a straight line stays
    straight however far apart the halves sit. Separation only decides WHERE on each roof the line
    lands, which is why it is a fitted input here and not an alignment constraint.

THE NUMBERS ARE FITTED FROM THE DESIGN SKETCH, NOT INVENTED. The sketch (two rounded rectangles with
four white strokes) was measured by classifying its pixels, recovering each shape's axes by PCA, and
splitting the crossing pair with a small Hough vote. Result: the strokes' page-space angles matched
in pairs to within 0.11°, i.e. the sketch really is two straight lines seen in two splayed frames.
Fitting ONE splay and TWO lines to all four measured strokes lands them within **0.166 mm max /
0.124 mm rms** — so these constants reproduce the drawing to well under a layer line.

Fitting rather than transcribing was deliberate: taken individually the four measured strokes imply
48.6° of splay from one pair and 50.8° from the other, so transcribing all four would bake that 2°
disagreement in and the puzzle would only *nearly* close. One fitted splay plus two fitted lines
makes collinearity exact by construction, and the sketch's own inconsistency shows up honestly as
that 0.166 mm residual instead of hiding as a permanent misalignment.

Every stroke runs out to the roof's edge on the GAP side, so the continuation reads as one line
rather than as two marks pointing at each other; each half's UPPER stroke additionally breaks
THROUGH the east arris, the switch-column side, which is the one edge actually notched. All of those
bounds are passed in (``x0_break``, ``y1_break``, ``x1_north``) like every other keep-out, so this
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


def line_in_canopy(side: str, index: int) -> tuple[float, float, float]:
    """Line ``index`` pulled back into a half's UN-MIRRORED canopy coords, as ``(a, b, c)`` meaning
    ``a·x + b·y = c``.

    This is the whole "equation": one assembled-frame line, expressed in each half's own frame. The
    two halves' strokes are then segments of the same line by construction, which is what makes the
    puzzle close exactly instead of approximately."""
    ang, off = PUZZLE_LINES[index]
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


def north_index(segs: list[tuple[tuple[float, float], tuple[float, float]]]) -> int:
    """Which stroke is the UPPER one on this roof — the northernmost by midpoint Y.

    Derived, not tabulated: the two halves are splayed, so the same assembled line is the upper one
    on one roof and the lower one on the other (today: line 0 on the left, line 1 on the right). A
    hand-written per-side index would silently point at the wrong stroke the moment the splay or the
    separation is re-fitted."""
    return max(range(len(segs)), key=lambda i: (segs[i][0][1] + segs[i][1][1]) / 2)


def strokes(side: str, x0: float, x1: float, y0: float, y1: float,
            x1_north: float | None = None, x0_break: float | None = None,
            y1_break: float | None = None
            ) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """Both strokes for a half, clipped to the safe rectangle, ordered south → north.

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


def assembled_offline_spread(side_strokes: dict[str, list]) -> list[float]:
    """For each line, how far its four endpoints deviate from being ONE straight line in the
    assembled frame. Zero is the whole point of the design, so it is worth being able to measure."""
    import numpy as np
    out = []
    for i in range(len(PUZZLE_LINES)):
        q = np.array([to_assembled(p, s) for s in ("left", "right") for p in side_strokes[s][i]])
        out.append(float(np.linalg.svd(q - q.mean(0), full_matrices=False)[1][1]))
    return out


# %%
if __name__ == "__main__":
    for s in ("left", "right"):
        print(s)
        for i, seg in enumerate(strokes(s, 14.1, 32.2, 60.3, 118.5, x1_north=36.2)):
            (ax, ay), (bx, by) = seg
            print(f"  line {i}: ({ax:6.2f},{ay:7.2f}) -> ({bx:6.2f},{by:7.2f})   "
                  f"dx/dy {(bx - ax) / (by - ay):+7.3f}")
