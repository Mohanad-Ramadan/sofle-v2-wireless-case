"""M17-3 connection mark as pure plan geometry.

The mark is drawn ONCE in the assembled pair frame: three narrows lines and one
steep bow curve. Each cover receives only the part of that figure that crosses its
own roof, so the two halves carry different pieces of one figure.

Canonical frame = the un-mirrored right-half coordinates a cover is built in. The
left cover is mirrored after its roof is cut, so its mark is computed canonically.
Imports only the standard library and ``constants`` (no build123d, no git).
"""
from __future__ import annotations

import math
from itertools import pairwise
from typing import Callable, Literal  # noqa: UP035 - plan limits imports to typing

from . import constants as C

Side = Literal["left", "right"]
Point = tuple[float, float]
Stroke = tuple[list[Point], float]
NARROW_SAMPLES = 900  # samples per narrows line over [-U_HALF, U_HALF]


def _rot(p: Point, th: float) -> Point:
    c, s = math.cos(th), math.sin(th)
    return (c*p[0]-s*p[1], s*p[0]+c*p[1])


_SPLAY = math.radians(C.COVER_MARK_SPLAY_HALF_DEG)


def to_assembled(pt: Point, side: Side) -> Point:
    """Canonical (built) point to the assembled pair frame."""
    if side == "left":
        return _rot((C.OUTER_WIDTH-pt[0], pt[1]), _SPLAY)
    q = _rot(pt, -_SPLAY)
    return (q[0]+C.COVER_MARK_RIGHT_OFFSET[0], q[1]+C.COVER_MARK_RIGHT_OFFSET[1])


def to_canonical(pt: Point, side: Side) -> Point:
    """Inverse of ``to_assembled``."""
    if side == "left":
        x, y = _rot(pt, -_SPLAY)
        return (C.OUTER_WIDTH-x, y)
    q = (pt[0]-C.COVER_MARK_RIGHT_OFFSET[0], pt[1]-C.COVER_MARK_RIGHT_OFFSET[1])
    return _rot(q, _SPLAY)


def design_frame() -> tuple[Point, Point, Point, float]:
    """Origin, unit U (left to right), unit V and half-distance E between encoder centres."""
    ex, ey = C.pcb_to_case(*C.SW_ENCODER_POS)
    lx, ly = to_assembled((ex, ey), "left")
    rx, ry = to_assembled((ex, ey), "right")
    dx, dy = rx-lx, ry-ly
    length = math.hypot(dx, dy)
    u = (dx/length, dy/length)
    return ((lx+rx)/2, (ly+ry)/2), u, (-u[1], u[0]), length/2


def _curve_lateral(t: float, amplitude: float) -> float:
    """Odd cubic about the seam inside the span; straight C1 run-out beyond it."""
    t_lo, t_hi, u_seam = C.COVER_MARK_LINE_A_SPAN
    h = max(u_seam, 1.0-u_seam)

    def core(uu: float) -> float:
        return amplitude*((uu-u_seam)/h)**3  # bows toward +normal

    u = (t-t_lo)/(t_hi-t_lo)
    if 0.0 <= u <= 1.0:
        return core(u)
    u_c = 0.0 if u < 0.0 else 1.0
    step = 1e-4 if u < 0.0 else -1e-4
    slope = (core(u_c+step)-core(u_c))/step
    return core(u_c)+slope*(u-u_c)


def _curve_point(t: float, amplitude: float | None = None) -> Point:
    angle, offset = C.COVER_MARK_LINE_A
    th = math.radians(angle)
    n = (math.cos(th), -math.sin(th))
    along = (math.sin(th), math.cos(th))
    a = C.COVER_MARK_CURVE_A if amplitude is None else amplitude
    d = offset+_curve_lateral(t, a)
    return (d*n[0]+t*along[0], d*n[1]+t*along[1])


def _analytic_curve() -> list[Point]:
    t_lo, t_hi, _ = C.COVER_MARK_LINE_A_SPAN
    lo, hi = t_lo-C.COVER_MARK_LINE_A_PAD, t_hi+C.COVER_MARK_LINE_A_PAD
    n = round((hi-lo)/C.COVER_MARK_SAMPLE_STEP)
    return [_curve_point(lo+(hi-lo)*k/n) for k in range(n+1)]


def default_curve_points(count: int = 15) -> list[Point]:
    """Editor start: ``count`` handles on the analytic bow (15 track it within 0.1 mm), ends
    beyond both covers so the grooves still run out through the edges."""
    t_lo, t_hi, _ = C.COVER_MARK_LINE_A_SPAN
    lo, hi = t_lo-C.COVER_MARK_LINE_A_PAD, t_hi+C.COVER_MARK_LINE_A_PAD
    return [_curve_point(lo+(hi-lo)*k/(count-1)) for k in range(count)]


CATMULL_SAMPLES = 400  # per span; the editor page samples identically


def catmull_rom(points: list[Point], samples: int = CATMULL_SAMPLES) -> list[Point]:
    """Centripetal Catmull-Rom through every handle (C1, no cusps or self-loops per span).

    Ends use reflected phantom handles so the curve starts and stops exactly on the end handles.
    The editor page (docs/previews/controller/mark_editor.html) runs the same arithmetic."""
    p = [tuple(q) for q in points]
    if len(p) < 2:
        raise ValueError("Bow A needs at least two handles")
    ext = [(2*p[0][0]-p[1][0], 2*p[0][1]-p[1][1]), *p,
           (2*p[-1][0]-p[-2][0], 2*p[-1][1]-p[-2][1])]
    out: list[Point] = [p[0]]
    for i in range(1, len(ext)-2):
        p0, p1, p2, p3 = ext[i-1], ext[i], ext[i+1], ext[i+2]
        t1 = max(math.dist(p0, p1), 1e-9)**.5
        t2 = t1+max(math.dist(p1, p2), 1e-9)**.5
        t3 = t2+max(math.dist(p2, p3), 1e-9)**.5
        for k in range(1, samples+1):
            t = t1+(t2-t1)*k/samples
            a1 = _lerp(p0, p1, 0.0, t1, t)
            a2 = _lerp(p1, p2, t1, t2, t)
            a3 = _lerp(p2, p3, t2, t3, t)
            b1 = _lerp(a1, a2, 0.0, t2, t)
            b2 = _lerp(a2, a3, t1, t3, t)
            out.append(_lerp(b1, b2, t1, t2, t))
    return out


def _lerp(a: Point, b: Point, ta: float, tb: float, t: float) -> Point:
    f = (t-ta)/(tb-ta)
    return (a[0]+(b[0]-a[0])*f, a[1]+(b[1]-a[1])*f)


def steep_curve() -> list[Point]:
    """Bow A in the assembled frame: the editor's handles if set, else the analytic bow.

    One curve for both covers, so each cover's piece continues the other's through the gap."""
    if C.COVER_MARK_CURVE_POINTS is None:
        return _analytic_curve()
    return catmull_rom(list(C.COVER_MARK_CURVE_POINTS))


def _eased_ramp(x: float) -> float:
    """max(x, 0) with a quadratic blend over +/-FAN_BLEND: same value and slope at both ends of
    the blend, so the fan has no slope break (C1) and is exact outside the blend."""
    w = C.COVER_MARK_FAN_BLEND
    if x <= -w:
        return 0.0
    if x >= w:
        return x
    return (x+w)**2/(4*w)


def narrow_v(u: float, v0: float, half: float, fan: float = 1.0) -> float:
    """Design-frame v at u for a narrows line with base offset v0.

    Bends out at each encoder (+/- ``half``), pinches toward PINCH_V near PINCH_U, then fans."""
    sign = math.copysign(1.0, v0)
    v = v0
    for cu in (-half, half):
        v += sign*C.COVER_MARK_BEND*math.exp(-(u-cu)**2/(2*C.COVER_MARK_BEND_SIGMA**2))
    du = u-C.COVER_MARK_PINCH_U
    v -= C.COVER_MARK_PINCH*(v0-C.COVER_MARK_PINCH_V)*math.exp(
        -du**2/(2*C.COVER_MARK_PINCH_SIGMA**2))
    v += C.COVER_MARK_S_BOW*(du/C.COVER_MARK_S_SCALE)**3
    v += fan*C.COVER_MARK_FAN*(v0-C.COVER_MARK_PINCH_V)*_eased_ramp(du)/C.COVER_MARK_FAN_SCALE
    return v


def narrows(v0: float, fan: float = 1.0) -> list[Point]:
    """One narrows line in the assembled frame, sampled over design u."""
    origin, u_hat, v_hat, half = design_frame()
    out: list[Point] = []
    for k in range(NARROW_SAMPLES):
        u = -C.COVER_MARK_U_HALF+2*C.COVER_MARK_U_HALF*k/(NARROW_SAMPLES-1)
        v = narrow_v(u, v0, half, fan)
        out.append((origin[0]+u*u_hat[0]+v*v_hat[0], origin[1]+u*u_hat[1]+v*v_hat[1]))
    return out


def point_in_polygon(p: Point, poly: list[Point]) -> bool:
    """Even-odd ray casting; the polygon is a closed ring given without repeating its first point."""
    inside = False
    ring = poly+poly[:1]
    for i in range(len(poly)):
        a, b = ring[i], ring[i+1]
        if (a[1] > p[1]) != (b[1] > p[1]) and p[0] < a[0]+(p[1]-a[1])*(b[0]-a[0])/(b[1]-a[1]):
            inside = not inside
    return inside


def _inside_runs(points: list[Point], inside: Callable[[Point], bool]) -> list[list[Point]]:
    """Maximal runs of consecutive samples for which ``inside`` holds."""
    runs: list[list[Point]] = []
    current: list[Point] = []
    for p in points:
        if inside(p):
            current.append(p)
        elif current:
            runs.append(current)
            current = []
    if current:
        runs.append(current)
    return [run for run in runs if len(run) >= 2]


def _seg_dist(p: Point, a: Point, b: Point) -> float:
    dx, dy = b[0]-a[0], b[1]-a[1]
    length2 = dx*dx+dy*dy
    if length2 == 0.0:
        return math.dist(p, a)
    t = min(1.0, max(0.0, ((p[0]-a[0])*dx+(p[1]-a[1])*dy)/length2))
    return math.dist(p, (a[0]+t*dx, a[1]+t*dy))


def _simplify(points: list[Point], tol: float) -> list[Point]:
    """Ramer-Douglas-Peucker, iterative; kept points are original samples."""
    keep = [False]*len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points)-1)]
    while stack:
        i, j = stack.pop()
        if j <= i+1:
            continue
        worst, at = -1.0, i
        for k in range(i+1, j):
            d = _seg_dist(points[k], points[i], points[j])
            if d > worst:
                worst, at = d, k
        if worst > tol:
            keep[at] = True
            stack += [(i, at), (at, j)]
    return [p for p, k in zip(points, keep) if k]


def _limit_length(runs: list[list[Point]], length: float) -> list[list[Point]]:
    """Keep the first ``length`` mm of the curve, walked from its northernmost end."""
    ordered = [run if run[0][1] >= run[-1][1] else run[::-1] for run in runs]
    ordered.sort(key=lambda run: -run[0][1])
    out: list[list[Point]] = []
    left = length
    for run in ordered:
        kept = [run[0]]
        for a, b in pairwise(run):
            step = math.dist(a, b)
            if step >= left:
                f = left/step if step else 0.0
                kept.append((a[0]+f*(b[0]-a[0]), a[1]+f*(b[1]-a[1])))
                left = 0.0
                break
            kept.append(b)
            left -= step
        if len(kept) >= 2:
            out.append(kept)
        if left <= 0.0:
            break
    return out


def line_v0(k: int) -> float:
    """Base offset of narrows line ``k`` (0 = south)."""
    return C.COVER_MARK_CENTER+C.COVER_MARK_SPACING*(k-(C.COVER_MARK_LINES-1)/2)


def default_line_points(k: int, count: int = 21) -> list[Point]:
    """Editor start for line ``k``: handles on its formula (21 track it within ~0.14 mm)."""
    line = narrows(line_v0(k), C.COVER_MARK_LINE_FAN[k])
    return [line[round(i*(len(line)-1)/(count-1))] for i in range(count)]


def line_curve(k: int) -> list[Point]:
    """Narrows line ``k`` in the assembled frame: the editor's handles if set, else the formula."""
    assert len(C.COVER_MARK_LINE_POINTS) == C.COVER_MARK_LINES, "one LINE_POINTS entry per line"
    handles = C.COVER_MARK_LINE_POINTS[k]
    return (narrows(line_v0(k), C.COVER_MARK_LINE_FAN[k]) if handles is None
            else catmull_rom(list(handles)))


def strokes(side: Side, inside: Callable[[Point], bool]) -> list[Stroke]:
    """Canonical strokes ``(points, width)`` for one cover, kept where ``inside`` holds."""
    marks = [(line_curve(k), C.COVER_MARK_WIDTH) for k in range(C.COVER_MARK_LINES)]
    marks.append((steep_curve(), C.COVER_MARK_CURVE_WIDTH))
    out: list[Stroke] = []
    for k, (assembled, width) in enumerate(marks):
        canonical = [to_canonical(p, side) for p in assembled]
        runs = _inside_runs(canonical, inside)
        if k == len(marks)-1 and side == "right" and C.COVER_MARK_RIGHT_CURVE_LENGTH is not None:
            runs = _limit_length(runs, C.COVER_MARK_RIGHT_CURVE_LENGTH)
        out += [(_simplify(run, C.COVER_MARK_SIMPLIFY_TOL), width) for run in runs]
    return out
