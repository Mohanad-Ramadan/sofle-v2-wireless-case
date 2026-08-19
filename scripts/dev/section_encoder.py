"""Y–Z sections through the encoder axis, one panel per cover variant.

The 3-D views flatten the thing that actually differs between these options — the gap under the
knob and the ring/pad profile beside it — so this cuts through the encoder centre and draws the
case in one colour and the knob phantom in another.

Usage:
    python scripts/dev/section_encoder.py <out.png> "label|case.stl|knob.stl" ...
"""
import sys
import struct
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sofle_case import constants as C
from sofle_case import knob as K
from sofle_case import encoder_phantom as E

ENC_X, ENC_Y = C.pcb_to_case(*C.SW_ENCODER_POS)
Y_HALF, Z_LO, Z_HI = 22.0, 13.5, 40.0


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


def slice_x(tris, x0):
    """Segments where triangles cross the plane X = x0, as (y, z) pairs."""
    segs = []
    d_all = tris[:, :, 0] - x0
    straddling = ~((d_all > 0).all(axis=1) | (d_all <= 0).all(axis=1))
    for t, d in zip(tris[straddling], d_all[straddling]):
        pts = []
        for a, b in ((0, 1), (1, 2), (2, 0)):
            if (d[a] > 0) != (d[b] > 0):
                f = d[a] / (d[a] - d[b])
                p = t[a] + f * (t[b] - t[a])
                pts.append((p[1], p[2]))
        if len(pts) == 2:
            segs.append(pts)
    return segs


out_png, specs = sys.argv[1], sys.argv[2:]
NCOLS = 4
nrows = (len(specs) + NCOLS - 1) // NCOLS
fig, axes = plt.subplots(nrows, NCOLS, figsize=(4.6 * NCOLS, 4.4 * nrows), squeeze=False)
for ax in axes.ravel()[len(specs):]:
    ax.set_axis_off()

for ax, spec in zip(axes.ravel(), specs):
    parts = spec.split("|")
    label, case_stl = parts[0], parts[1]
    extra_colours = ["#c47a12", "#5a5a63", "#2e8b57"]   # knob, encoder, keycaps
    for path, colour, width in [(case_stl, "#1f4e79", 1.5)] + \
            [(p, extra_colours[min(i, len(extra_colours) - 1)], 1.3)
             for i, p in enumerate(parts[2:])]:
        for (y0, z0), (y1, z1) in slice_x(load_stl(path), ENC_X):
            ax.plot([y0, y1], [z0, z1], color=colour, linewidth=width, solid_capstyle="round")
    ax.axhline(C.COVER_TOP_Z, color="#999", linewidth=0.6, linestyle=":")
    ax.set_xlim(ENC_Y - Y_HALF, ENC_Y + Y_HALF)
    ax.set_ylim(Z_LO, Z_HI)
    ax.set_aspect("equal")
    ax.set_title(label, fontsize=9)
    ax.set_xlabel("case Y (mm)", fontsize=8)
    ax.tick_params(labelsize=7)

# One decimal on the deck, deliberately. At :.0f this read "deck Z16" for a deck that has been
# 16.4 since MAIN_RIM_Z moved — every older sheet in docs/encoder-illustration says Z16 and none of
# them records that the stack had shifted under it. A label that rounds away a real move is worse
# than no label. Same for the shaft: "cut to 20.0" reads like an instruction when 20.0 IS the
# as-bought length and no cut is wanted.
_shaft = (f"shaft uncut at {E.SHAFT_LEN:.1f}" if K.shaft_trim_needed() <= 0
          else f"shaft CUT to {K.shaft_len_for_seating():.1f} from {E.SHAFT_LEN:.1f}")
fig.suptitle(f"Section through the encoder axis (X = {ENC_X:.1f}); dotted line = deck Z"
             f"{C.COVER_TOP_Z:.1f}. Blue = case, orange = Ø{K.KNOB_OD:.0f}×{K.KNOB_H:.0f} metal "
             f"knob, grey = EC11 phantom ({_shaft})",
             fontsize=11)
fig.tight_layout()
fig.savefig(out_png, dpi=140, bbox_inches="tight", facecolor="white")
print("wrote", out_png)
