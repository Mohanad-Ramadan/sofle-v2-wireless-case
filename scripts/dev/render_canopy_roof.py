"""The canopy roofs' puzzle marks, offline: raking-light renders plus a MEASURED depth profile.

There is no headless browser on this machine, so the lab the curve was chosen in cannot be re-run
here. This is the substitute, and it is deliberately not a re-plot of the same maths the case is
built from: the renders come from the STL, and so does the depth curve — sampled off the mesh by
dropping a vertical probe on the groove and beside it — which is then laid over the analytic
``canopy.puzzle_depth_at``. If the cutter and the depth field ever disagree, this picture shows it;
a plot of the model against itself never could.

Three rows. The raking render is the only one that comes from the STL as a picture; the plan row
draws the marks themselves at their true 1.0 mm width, which is the view the curve was chosen in and
the one a shaded render cannot give (a 0.5 mm groove on a tessellated roof is mostly triangle noise).
The profile row is the check: measured depth laid over the analytic ``puzzle_depth_at``, and the two
should sit on top of each other.

The profile stops where the mark leaves the FLAT roof — on the right half at y ≈ 74, where the stroke
has run west onto the shoulder facet on its way down the ramp — because past that arris the surface
has already fallen away below the cutter and there is nothing to measure. The fade to zero at the
ramp foot happens south of that, out on the facet, and it is asserted rather than drawn:
``test_the_groove_dies_exactly_at_the_ramp_foot``.

Usage:
    python scripts/dev/render_canopy_roof.py <out.png> <right_top.stl> [left_top.stl]
"""
import struct
import sys

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from sofle_case import canopy as CAN
from sofle_case import constants as C

# The frame: the whole roof strip plus a little air, from under the ramp foot to past the north
# wall. Fixed, so two halves — or the same half before and after a change — land at the same scale.
XLO, XHI = CAN.CANOPY_WEST_OUTER_X - 2.0, CAN.CANOPY_EAST_X + 3.0
YLO, YHI = CAN.CANOPY_RAMP_FOOT_Y - 3.0, CAN.CANOPY_NORTH_OUTER_Y + 2.0
ZLO = C.COVER_TOP_Z - 2.0
KEEP_PAD = 3.0

# Raking, from the north-west and low: a 0.23–0.50 mm groove has no silhouette of its own, so it is
# only visible as the shadow its own wall casts. Straight-down light renders it invisible.
LIGHT = np.array([0.62, -0.30, 0.42])
VIEWS = [(28, -118, "3/4 from the north-west, raking")]


def load_stl(path):
    with open(path, "rb") as f:
        f.read(80)
        n = struct.unpack("<I", f.read(4))[0]
        data = np.frombuffer(f.read(n * 50), dtype=np.uint8).reshape(n, 50)
    tris = np.zeros((n, 3, 3), np.float32)
    for i in range(3):
        for j in range(3):
            tris[:, i, j] = data[:, 12 + i * 12 + j * 4: 16 + i * 12 + j * 4] \
                .copy().view("<f4").ravel()
    return tris


def unmirror(tris, side):
    """The LEFT top part is mirrored in X by ``case.build_top_part``; the canopy is modelled
    un-mirrored, so put it back before framing it against canopy coordinates."""
    if side != "left":
        return tris
    out = tris.copy()
    out[:, :, 0] = C.OUTER_WIDTH - out[:, :, 0]
    return out


def crop(tris):
    """Keep triangles whose vertices all sit inside frame+pad, and nothing below the deck. The pad
    matters: dropping a triangle the moment one vertex leaves the frame punches holes in the big
    flat faces, and the axis limits enforce the frame itself."""
    vx, vy, vz = tris[:, :, 0], tris[:, :, 1], tris[:, :, 2]
    keep = ((vx >= XLO - KEEP_PAD) & (vx <= XHI + KEEP_PAD)
            & (vy >= YLO - KEEP_PAD) & (vy <= YHI + KEEP_PAD)).all(axis=1)
    keep &= (vz >= ZLO).all(axis=1)
    return tris[keep]


def shade(tris, base=(0.34, 0.58, 0.86)):
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    ln = np.linalg.norm(n, axis=1, keepdims=True)
    ln[ln == 0] = 1
    b = np.clip((n / ln) @ (LIGHT / np.linalg.norm(LIGHT)), 0, 1) * 0.72 + 0.28
    return np.clip(np.asarray(base)[None, :] * b[:, None], 0, 1)


def top_z(tris, x, y):
    """The highest surface over ``(x, y)`` — a vertical probe, dropped on the mesh.

    Point-in-triangle by sign of the three edge cross products, on the XY projection, then the
    plane's own Z at that point. Vectorised over the whole mesh because it is called a few hundred
    times and a Python loop over 60k triangles per call is not worth the wait."""
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]

    def side(p, q):
        return (q[:, 0] - p[:, 0]) * (y - p[:, 1]) - (q[:, 1] - p[:, 1]) * (x - p[:, 0])

    s1, s2, s3 = side(a, b), side(b, c), side(c, a)
    inside = ((s1 >= 0) & (s2 >= 0) & (s3 >= 0)) | ((s1 <= 0) & (s2 <= 0) & (s3 <= 0))
    hit = tris[inside]
    if not len(hit):
        return None
    n = np.cross(hit[:, 1] - hit[:, 0], hit[:, 2] - hit[:, 0])
    flat = np.abs(n[:, 2]) < 1e-9
    z = np.where(flat, hit[:, 0, 2],
                 hit[:, 0, 2] - (n[:, 0] * (x - hit[:, 0, 0])
                                 + n[:, 1] * (y - hit[:, 0, 1])) / np.where(flat, 1.0, n[:, 2]))
    return float(z.max())


def walk(seg, t):
    steps = [float(np.hypot(b[0] - a[0], b[1] - a[1])) for a, b in zip(seg, seg[1:])]
    want = sum(steps) * t
    for (a, b), d in zip(zip(seg, seg[1:]), steps):
        if want <= d or d == 0:
            f = 0.0 if d == 0 else want / d
            return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
        want -= d
    return seg[-1]


def depth_profile(tris, side, index, n=120):
    """Measured groove depth against Y, along one stroke, PERPENDICULAR to the roof.

    One probe per station, against the roofline's own analytic Z rather than against a second probe
    beside the groove: a sideways probe reads whatever else is there — the other stroke, the east
    notch, the north wall — and turns a clean profile into a picture of its own failures. The
    measured half is still the STL's top surface, which is the thing being checked.

    Divided by √(1+m²) because the roof is tilted and a vertical difference over-reads by 1/cos θ.
    Stations off the flat roof are dropped, not plotted as zero: at the arrises the surface has
    already fallen away below the cutter, so there is nothing there to measure."""
    seg = CAN.canopy_puzzle_strokes(side)[index]
    z_ridge = CAN.canopy_ridge_top_z(side)
    x_w = CAN.CANOPY_WEST_OUTER_X + CAN.canopy_top_chamfer(side)[1] + 0.3
    ys, got, want = [], [], []
    for k in range(n):
        x, y = walk(seg, k / (n - 1))
        if not (x_w < x < CAN.CANOPY_EAST_X - 0.3) or y > CAN.CANOPY_NORTH_OUTER_Y - 1.5:
            continue
        top = top_z(tris, x, y)
        if top is None:
            continue
        m = CAN._roofline_slope(y, z_ridge)
        d = (CAN._canopy_roof_z(y, z_ridge) - top) / float(np.sqrt(1 + m * m))
        if not (-0.05 <= d <= CAN.CANOPY_PUZZLE_DEPTH + 0.2):
            continue                       # the probe is not on the roof (a notch mouth, a wall)
        ys.append(y)
        got.append(d)
        want.append(CAN.puzzle_depth_at(y, z_ridge))
    return ys, got, want


def main() -> None:
    out_png, stls = sys.argv[1], sys.argv[2:]
    if not stls:
        raise SystemExit(__doc__)
    halves = [("right", stls[0])] + ([("left", stls[1])] if len(stls) > 1 else [])

    fig = plt.figure(figsize=(6.2 * len(halves), 12.5))
    grid = (3, len(halves))
    for col, (side, path) in enumerate(halves):
        tris = unmirror(load_stl(path), side)
        shown = crop(tris)
        zhi = float(shown[:, :, 2].max())
        # NOT a cube. The roof strip is 27 × 66 × 12 mm, and forcing equal axis ranges (the usual
        # trick for keeping proportions honest) shrinks it to a splinter in the middle of the frame.
        # ``set_box_aspect`` carries the true proportions instead, so nothing is stretched.
        for row, (el, az, title) in enumerate(VIEWS):
            ax = fig.add_subplot(*grid, row * len(halves) + col + 1, projection="3d")
            ax.add_collection3d(Poly3DCollection(shown, facecolors=shade(shown),
                                                 edgecolors="#12304f", linewidths=0.10))
            ax.set_xlim(XLO, XHI)
            ax.set_ylim(YLO, YHI)
            ax.set_zlim(ZLO, zhi)
            ax.set_box_aspect((XHI - XLO, YHI - YLO, zhi - ZLO))
            ax.view_init(elev=el, azim=az)
            ax.set_axis_off()
            ax.set_title(f"{side} — {title}", fontsize=10)

        # THE MARK AS A DRAWING, from the model rather than the mesh, at the width it is cut. This is
        # the view the amplitude was chosen in: a shaded render of a 0.5 mm groove on a tessellated
        # roof shows tessellation, and the shape of the mark is what there is to judge.
        segs = CAN.canopy_puzzle_strokes(side)
        ax = fig.add_subplot(*grid, len(halves) + col + 1)
        x_w = CAN.CANOPY_WEST_OUTER_X + CAN.canopy_top_chamfer(side)[1]
        for x in (CAN.CANOPY_WEST_OUTER_X, x_w, CAN.CANOPY_EAST_X):
            ax.axvline(x, color="#bbb", linewidth=0.8,
                       linestyle="-" if x != x_w else "--")
        for y in (CAN.CANOPY_RAMP_FOOT_Y, CAN.CANOPY_RAMP_TOP_Y, CAN.CANOPY_NORTH_OUTER_Y):
            ax.axhline(y, color="#bbb", linewidth=0.8,
                       linestyle="-" if y == CAN.CANOPY_NORTH_OUTER_Y else ":")
        for i, seg in enumerate(segs):
            xs, ys_ = [q[0] for q in seg], [q[1] for q in seg]
            # linewidth in POINTS = mm × (dpi-independent) points per data unit, set after the
            # limits are fixed, so the stroke is drawn at the width it is actually cut.
            ax.plot(xs, ys_, color=("#1f4e79", "#c47a12")[i % 2], solid_capstyle="butt",
                    linewidth=1.0, label=f"line {i}")
        ax.set_xlim(XLO, XHI)
        ax.set_ylim(YLO, YHI)
        ax.set_aspect("equal")
        ax.set_title(f"{side} — the mark as a drawing (plan)", fontsize=10)
        ax.set_xlabel("case X (mm)   ·   dashed: the shoulder facet's top line")
        ax.legend(fontsize=8, loc="lower right")

        # The ramp stroke: the one whose south end goes furthest down the slope.
        index = min(range(len(segs)), key=lambda i: min(p[1] for p in segs[i]))
        ys, got, want = depth_profile(tris, side, index)
        ax = fig.add_subplot(*grid, 2 * len(halves) + col + 1)
        ax.plot(ys, want, color="#c47a12", linewidth=2.0, label="puzzle_depth_at (allowed)")
        ax.plot(ys, got, color="#1f4e79", linewidth=1.3, marker=".", markersize=3,
                label="measured off the STL")
        ax.axvline(CAN.CANOPY_RAMP_FOOT_Y, color="#999", linestyle=":", linewidth=0.8)
        ax.axvline(CAN.CANOPY_RAMP_TOP_Y, color="#999", linestyle=":", linewidth=0.8)
        ax.set_xlabel("case Y (mm)   ·   dotted: ramp foot and ramp top")
        ax.set_ylabel("groove depth ⊥ to the roof (mm)")
        ax.set_title(f"{side} line {index} — the mark fading out onto the ramp", fontsize=10)
        ax.set_ylim(-0.05, CAN.CANOPY_PUZZLE_DEPTH + 0.15)
        ax.grid(alpha=0.25)
        ax.legend(fontsize=8)

    fig.tight_layout()
    fig.savefig(out_png, dpi=140, bbox_inches="tight", facecolor="white")
    print("wrote", out_png)


if __name__ == "__main__":
    main()
