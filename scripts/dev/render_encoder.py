"""Shaded renders of the encoder region, three fixed views, for comparing bezel styles.

Usage:
    python scripts/dev/render_encoder.py <stl> <out.png> "<title>" [extra.stl ...]

Extra STLs (e.g. a knob) are rendered in a second colour on top of the case, so the
knob-to-plateau reveal is visible. The crop box is fixed around the encoder centre so
every variant lands in the same frame at the same scale.
"""
import sys
import struct
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from sofle_case import constants as C

# Fixed frame around the encoder: wide enough to catch the canopy ramp foot (north),
# the neighbouring switch window (east) and a stretch of plain cover (south).
ENC_X, ENC_Y = C.pcb_to_case(*C.SW_ENCODER_POS)
HALF_X, SOUTH, NORTH = 15.0, 13.0, 17.0
XLO, XHI = ENC_X - HALF_X, ENC_X + HALF_X
YLO, YHI = ENC_Y - SOUTH, ENC_Y + NORTH
# Triangles are kept on a LARGER box than the frame and the view is then clipped to the frame:
# dropping a triangle the moment one vertex leaves the frame punches holes in every big flat
# face, and keeping it by centroid leaves long spikes shooting out of the picture.
KEEP_PAD = 26.0
ZLO, ZHI = C.COVER_TOP_Z - 4.0, None   # ZHI filled in from the mesh (knob crown height varies)

VIEWS = [
    (24, -68, "3/4 from front-right"),
    (6, -90, "South elevation (how it reads from the user)"),
    (72, -90, "Near-plan (footprint + reveal)"),
]


def load_stl(path):
    with open(path, "rb") as f:
        f.read(80)
        n = struct.unpack("<I", f.read(4))[0]
        data = np.frombuffer(f.read(n * 50), dtype=np.uint8).reshape(n, 50)
    tris = np.zeros((n, 3, 3), np.float32)
    for i in range(3):
        for j in range(3):
            tris[:, i, j] = data[:, 12 + i * 12 + j * 4: 16 + i * 12 + j * 4].copy().view("<f4").ravel()
    return tris


def crop(tris):
    """Keep triangles fully inside frame+KEEP_PAD, and drop anything below the deck: the frame
    itself is enforced by the axis limits, so nothing pokes out and nothing is punched through."""
    vx, vy, vz = tris[:, :, 0], tris[:, :, 1], tris[:, :, 2]
    keep = ((vx >= XLO - KEEP_PAD) & (vx <= XHI + KEEP_PAD)
            & (vy >= YLO - KEEP_PAD) & (vy <= YHI + KEEP_PAD)).all(axis=1)
    keep &= (vz >= ZLO).all(axis=1)
    return tris[keep]


def shade(tris, base, light=np.array([0.45, -0.65, 0.62])):
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    ln = np.linalg.norm(n, axis=1, keepdims=True)
    ln[ln == 0] = 1
    n = n / ln
    light = light / np.linalg.norm(light)
    b = np.clip(n @ light, 0, 1) * 0.7 + 0.3
    return np.clip(np.asarray(base)[None, :] * b[:, None], 0, 1)


CASE_BASE = (0.32, 0.56, 0.86)
KNOB_BASE = (0.95, 0.62, 0.22)
ENCODER_BASE = (0.42, 0.42, 0.46)   # the EC11 phantom
EXTRA_BASES = [KNOB_BASE, ENCODER_BASE]

def frame_box(meshes, z_top: float | None = None):
    """The fixed XY frame plus a Z ceiling — shared with the contact-sheet script so a variant
    always lands at the same scale."""
    if z_top is None:
        pts = np.concatenate([m.reshape(-1, 3) for m, _ in meshes if len(m)])
        inframe = pts[(pts[:, 0] >= XLO) & (pts[:, 0] <= XHI)
                      & (pts[:, 1] >= YLO) & (pts[:, 1] <= YHI)]
        z_top = float(inframe[:, 2].max())
    mn, mx = np.array([XLO, YLO, ZLO]), np.array([XHI, YHI, z_top])
    return (mn + mx) / 2, (mx - mn).max() / 2


def draw(ax, meshes, ctr, rad, elev, azim) -> None:
    """ONE collection for everything: matplotlib depth-sorts triangles inside a collection but
    only ranks whole collections against each other, so a separate knob collection ends up hidden
    behind the canopy roof instead of sitting on the bezel."""
    ax.add_collection3d(Poly3DCollection(
        np.concatenate([t for t, _ in meshes if len(t)]),
        facecolors=np.concatenate([shade(t, b) for t, b in meshes if len(t)]),
        edgecolors="#12304f", linewidths=0.12))
    ax.set_xlim(ctr[0] - rad, ctr[0] + rad)
    ax.set_ylim(ctr[1] - rad, ctr[1] + rad)
    ax.set_zlim(ctr[2] - rad, ctr[2] + rad)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()


def load_variant(case_stl: str, extras: list[str]):
    """First extra is the knob, second the encoder phantom — each gets its own colour."""
    meshes = [(crop(load_stl(case_stl)), CASE_BASE)]
    for k, extra in enumerate(extras):
        meshes.append((crop(load_stl(extra)), EXTRA_BASES[min(k, len(EXTRA_BASES) - 1)]))
    return meshes


def main() -> None:
    case_stl, out_png = sys.argv[1], sys.argv[2]
    title = sys.argv[3] if len(sys.argv) > 3 else ""
    meshes = load_variant(case_stl, sys.argv[4:])
    ctr, rad = frame_box(meshes)

    fig = plt.figure(figsize=(16.5, 6.0))
    for k, (el, az, vtitle) in enumerate(VIEWS, 1):
        ax = fig.add_subplot(1, 3, k, projection="3d")
        draw(ax, meshes, ctr, rad, el, az)
        ax.set_title(vtitle, fontsize=10)
    fig.suptitle(title, fontsize=13)
    fig.tight_layout()
    fig.savefig(out_png, dpi=140, bbox_inches="tight", facecolor="white")
    print("wrote", out_png)


if __name__ == "__main__":
    main()
