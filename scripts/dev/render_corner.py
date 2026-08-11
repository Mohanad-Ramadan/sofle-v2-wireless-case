"""Zoomed shaded render of a corner region of the STL, multiple angles."""
import sys, struct
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


def load_stl(path):
    with open(path, "rb") as f:
        f.read(80); n = struct.unpack("<I", f.read(4))[0]
        data = np.frombuffer(f.read(n * 50), dtype=np.uint8).reshape(n, 50)
    tris = np.zeros((n, 3, 3), np.float32)
    for i in range(3):
        for j in range(3):
            tris[:, i, j] = data[:, 12 + i*12 + j*4: 16 + i*12 + j*4].copy().view("<f4").ravel()
    return tris


def shade(tris, light=np.array([0.5, -0.6, 0.6])):
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    ln = np.linalg.norm(n, axis=1, keepdims=True); ln[ln == 0] = 1
    n = n / ln; light = light / np.linalg.norm(light)
    return np.clip(n @ light, 0, 1) * 0.7 + 0.3


# crop box (case coords)
xlo, xhi, ylo, yhi = [float(a) for a in sys.argv[3:7]]
tris = load_stl(sys.argv[1])
# keep only triangles fully inside the crop box (no boundary-straddling spikes)
vx, vy = tris[:, :, 0], tris[:, :, 1]
keep = ((vx >= xlo) & (vx <= xhi) & (vy >= ylo) & (vy <= yhi)).all(axis=1)
tris = tris[keep]
b = shade(tris)
base = np.array([0.32, 0.56, 0.86])
colors = np.clip(base[None, :] * b[:, None], 0, 1)

views = [(14, -120, "SW thumb wall, straight-on"), (24, -80, "low 3/4 from front")]
fig = plt.figure(figsize=(15, 6.6))
for k, (el, az, ti) in enumerate(views, 1):
    ax = fig.add_subplot(1, 2, k, projection="3d")
    pc = Poly3DCollection(tris, facecolors=colors, edgecolors="#0d2c4d", linewidths=0.15)
    ax.add_collection3d(pc)
    mn = tris.reshape(-1, 3).min(0); mx = tris.reshape(-1, 3).max(0)
    c = (mn + mx) / 2; r = (mx - mn).max() / 2
    ax.set_xlim(c[0]-r, c[0]+r); ax.set_ylim(c[1]-r, c[1]+r); ax.set_zlim(c[2]-r, c[2]+r)
    ax.set_box_aspect((1, 1, 1)); ax.view_init(elev=el, azim=az); ax.set_axis_off()
    ax.set_title(ti, fontsize=10)
fig.suptitle(sys.argv[7] if len(sys.argv) > 7 else "", fontsize=12)
fig.tight_layout()
fig.savefig(sys.argv[2], dpi=140, bbox_inches="tight", facecolor="white")
print("wrote", sys.argv[2])
