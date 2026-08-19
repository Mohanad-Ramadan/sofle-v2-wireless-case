"""Contact sheet: every encoder variant in the same two views, same frame, same scale.

Usage:
    python scripts/dev/render_encoder_sheet.py <out.png> "label|case.stl[|knob.stl]" ...
"""
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, "scripts/dev")
from render_encoder import load_variant, frame_box, draw, XLO, XHI, YLO, YHI

# (elev, azim, show_knob). The last row drops the knob: it is the only way to see what the cover
# itself does — with the knob on, the Ø13 disc covers every deck feature inside its own radius.
# It covers less than the sheet's first draft assumed: Ø13 sits well inside the Ø18.2 aperture, so
# the knob-on rows still show the annulus, and the knob-off row is about the deck beyond it.
ROWS = [(24, -68, True), (6, -90, True), (88, -90, False)]

out_png, specs = sys.argv[1], sys.argv[2:]
cols = []
for spec in specs:
    parts = spec.split("|")   # not ":" — labels contain colons
    cols.append((parts[0], load_variant(parts[1], parts[2:])))

# One Z ceiling for every panel, so heights are comparable across variants.
z_top = 0.0
for _, meshes in cols:
    pts = np.concatenate([m.reshape(-1, 3) for m, _ in meshes if len(m)])
    inf = pts[(pts[:, 0] >= XLO) & (pts[:, 0] <= XHI) & (pts[:, 1] >= YLO) & (pts[:, 1] <= YHI)]
    z_top = max(z_top, float(inf[:, 2].max()))
ctr, rad = frame_box(None, z_top=z_top)

fig = plt.figure(figsize=(4.4 * len(cols), 4.2 * len(ROWS)))
for c, (label, meshes) in enumerate(cols):
    for r, (el, az, show_knob) in enumerate(ROWS):
        ax = fig.add_subplot(len(ROWS), len(cols), r * len(cols) + c + 1, projection="3d")
        draw(ax, meshes if show_knob else meshes[:1], ctr, rad, el, az)
        if r == 0:
            ax.set_title(label, fontsize=11)
        if r == len(ROWS) - 1 and not show_knob:
            ax.set_title("plan, knob removed", fontsize=8, color="#666")
fig.tight_layout()
fig.savefig(out_png, dpi=130, bbox_inches="tight", facecolor="white")
print("wrote", out_png)
