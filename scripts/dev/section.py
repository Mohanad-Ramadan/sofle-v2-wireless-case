"""Y-Z cross-section of the case at a given X, showing the front facet profile."""
import struct
import sys

import matplotlib
import numpy as np

from sofle_case.constants import FRONT_FACET_DROP, MAIN_RIM_Z

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def load_stl(path):
    with open(path, "rb") as f:
        f.read(80); n = struct.unpack("<I", f.read(4))[0]
        data = np.frombuffer(f.read(n * 50), dtype=np.uint8).reshape(n, 50)
    tris = np.zeros((n, 3, 3), np.float32)
    for i in range(3):
        for j in range(3):
            tris[:, i, j] = data[:, 12 + i*12 + j*4: 16 + i*12 + j*4].copy().view("<f4").ravel()
    return tris


def slice_x(tris, x0):
    segs = []
    for t in tris:
        d = t[:, 0] - x0
        pos = d > 0
        if pos.all() or (~pos).all():
            continue
        pts = []
        for a, b in ((0, 1), (1, 2), (2, 0)):
            if (d[a] > 0) != (d[b] > 0):
                f = d[a] / (d[a] - d[b])
                p = t[a] + f * (t[b] - t[a])
                pts.append((p[1], p[2]))
        if len(pts) == 2:
            segs.append(pts)
    return segs


tris = load_stl(sys.argv[1])
xs = [40.0, 80.0]  # two X stations through the key field
rim_z = MAIN_RIM_Z
front_facet_toe_z = MAIN_RIM_Z - FRONT_FACET_DROP
fig, axes = plt.subplots(1, len(xs), figsize=(13, 5))
for ax, x0 in zip(axes, xs):
    for (y0, z0), (y1, z1) in slice_x(tris, x0):
        ax.plot([y0, y1], [z0, z1], color="#1f4e79", lw=1.3)
    ax.axhline(rim_z, color="#bbb", ls=":", lw=0.8)
    ax.axhline(front_facet_toe_z, color="#e07b39", ls="--", lw=0.9)
    ax.text(2, rim_z + 0.4, f"rim {rim_z:.1f}", fontsize=8, color="#888")
    ax.text(
        2,
        front_facet_toe_z + 0.4,
        f"front facet toe {front_facet_toe_z:.1f}",
        fontsize=8,
        color="#e07b39",
    )
    ax.set_aspect("equal"); ax.set_title(f"Y-Z section at X={x0:.0f}  (front = low Y)")
    ax.set_xlabel("case Y (front → back)"); ax.set_ylabel("Z")
    ax.grid(alpha=0.2)
fig.suptitle("Front (south) facet halves the palm-facing wall; back stays full height", fontsize=12)
fig.tight_layout()
fig.savefig(sys.argv[2], dpi=130, bbox_inches="tight", facecolor="white")
print("wrote", sys.argv[2])
