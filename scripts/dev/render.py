"""Offline shaded render of an STL from a few angles (no interactive viewer)."""
import sys, struct
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


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


def shade(tris, light=np.array([0.4, -0.7, 0.6])):
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    ln = np.linalg.norm(n, axis=1, keepdims=True)
    ln[ln == 0] = 1
    n = n / ln
    light = light / np.linalg.norm(light)
    b = np.clip(n @ light, 0, 1) * 0.75 + 0.25
    return b


def render(tris, elev, azim, ax, title):
    b = shade(tris)
    base = np.array([0.30, 0.55, 0.85])
    colors = base[None, :] * b[:, None]
    colors = np.clip(colors, 0, 1)
    pc = Poly3DCollection(tris, facecolors=colors, edgecolors="none", linewidths=0)
    ax.add_collection3d(pc)
    mn = tris.reshape(-1, 3).min(0); mx = tris.reshape(-1, 3).max(0)
    ctr = (mn + mx) / 2; r = (mx - mn).max() / 2
    ax.set_xlim(ctr[0] - r, ctr[0] + r)
    ax.set_ylim(ctr[1] - r, ctr[1] + r)
    ax.set_zlim(ctr[2] - r, ctr[2] + r)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    ax.set_title(title, fontsize=11)


tris = load_stl(sys.argv[1])
fig = plt.figure(figsize=(15, 5.2))
views = [
    (22, -60, "3/4 from front-right (south facet + perimeter draft)"),
    (6, -90, "South elevation (palm-facing front)"),
    (6, 0, "East side elevation ('tall from the side' view)"),
]
for k, (el, az, ti) in enumerate(views, 1):
    ax = fig.add_subplot(1, 3, k, projection="3d")
    render(tris, el, az, ax, ti)
fig.tight_layout()
fig.savefig(sys.argv[2], dpi=130, bbox_inches="tight", facecolor="white")
print("wrote", sys.argv[2])
