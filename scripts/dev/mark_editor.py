"""Data export and apply step for docs/previews/controller/mark_editor.html.

    python scripts/dev/mark_editor.py export           # refresh mark_editor.js from production
    python scripts/dev/mark_editor.py apply FILE.json  # write the editor's handles into constants.py

Every mark curve (the three narrows lines and Bow A) can be reshaped with handles in the
assembled pair frame. A curve left untouched exports as null and keeps its formula
(COVER_MARK_LINE_POINTS[k] / COVER_MARK_CURVE_POINTS = None). COVER_MARK_RIGHT_CURVE_LENGTH still
limits only the right cover's Bow A piece.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from sofle_case import constants as C
from sofle_case import cover_mark as CM
from sofle_case import mcu_encoder_cover as MEC

ROOT = Path(__file__).resolve().parents[2]
PAGE_DATA = ROOT/"docs/previews/controller/mark_editor.js"
CONSTANTS = ROOT/"src/sofle_case/constants.py"


def _r(points, nd=4):
    return [[round(x, nd), round(y, nd)] for x, y in points]


def export() -> None:
    outer = MEC._cover_outer_polygon()
    run = C.COVER_SIDE_CHAMFER_RUN
    chamfer_top = MEC._cover_polygon(west_inset=run, east_inset=run, north_inset=run, south_inset=run)
    ex, ey, _, _ = MEC._encoder_bbox()
    half = max(C.COVER_MARK_WIDTH, C.COVER_MARK_CURVE_WIDTH)/2
    north = max(y for _, y in outer)
    names = ["Line 1 (south)", "Line 2", "Line 3 (north)"] if C.COVER_MARK_LINES == 3 else \
        [f"Line {k+1}" for k in range(C.COVER_MARK_LINES)]
    curves = []
    for k in range(C.COVER_MARK_LINES):
        handles = C.COVER_MARK_LINE_POINTS[k]
        curves.append({"name": names[k], "kind": "line", "width": C.COVER_MARK_WIDTH,
                       "formula": _r(CM.narrows(CM.line_v0(k))),
                       "default_handles": _r(CM.default_line_points(k)),
                       "handles": None if handles is None else _r(handles)})
    bow = C.COVER_MARK_CURVE_POINTS
    curves.append({"name": "Bow A", "kind": "bow", "width": C.COVER_MARK_CURVE_WIDTH,
                   "formula": _r(CM._analytic_curve()[::2]),
                   "default_handles": _r(CM.default_curve_points()),
                   "handles": None if bow is None else _r(bow)})
    data = {
        "splay_deg": C.COVER_MARK_SPLAY_HALF_DEG, "right_offset": list(C.COVER_MARK_RIGHT_OFFSET),
        "outer_width": C.OUTER_WIDTH, "samples": CM.CATMULL_SAMPLES,
        "outline": _r(outer), "chamfer_top": _r(chamfer_top),       # canonical; page maps per side
        "encoder": [ex, ey], "shaft_r": C.COVER_SHAFT_CUTOUT_DIA/2,
        "curves": curves, "length": C.COVER_MARK_RIGHT_CURVE_LENGTH,
        "inside": {"x0": min(x for x, _ in outer)-C.COVER_MARK_RUN_OUT,
                   "x1": max(x for x, _ in outer)+C.COVER_MARK_RUN_OUT,
                   "y0": min(y for _, y in outer)-C.COVER_MARK_RUN_OUT,
                   "y1": max(y for _, y in outer)+C.COVER_MARK_RUN_OUT,
                   "ex": ex, "ey": ey, "quiet": C.COVER_SHAFT_CUTOUT_DIA/2+C.COVER_MARK_QUIET_R+half,
                   "mcu_x": C.pcb_to_case(*C.MCU_POS)[0], "usb_half": C.COVER_USB_PORT_W/2+1.0+half,
                   "usb_y": north-C.COVER_NORTH_WALL-1.0-half},
        "depth": C.COVER_MARK_DEPTH,
    }
    PAGE_DATA.write_text("window.MARK = "+json.dumps(data)+";\n")
    print(f"wrote {PAGE_DATA}")


def _points(pts) -> str:
    return "None" if pts is None else "("+", ".join(f"({x:.4f}, {y:.4f})" for x, y in pts)+",)"


def apply(path: str) -> None:
    v = json.loads(Path(path).read_text())
    lines = v["lines"]
    assert len(lines) == C.COVER_MARK_LINES, "one entry per narrows line"
    values = (("COVER_MARK_CURVE_POINTS: tuple[tuple[float, float], ...] | None", _points(v["bow"])),
              ("COVER_MARK_LINE_POINTS: tuple[tuple[tuple[float, float], ...] | None, ...]",
               "("+", ".join(_points(p) for p in lines)+",)"),
              ("COVER_MARK_RIGHT_CURVE_LENGTH: float | None",
               "None" if v.get("length") is None else f"{float(v['length']):.2f}"))
    text = CONSTANTS.read_text()
    for name, value in values:
        pattern = rf"^({re.escape(name)} = )([^#\n]*?)(\s*#.*)?$"
        text, n = re.subn(pattern, lambda m: m.group(1)+value+(m.group(3) or ""), text,
                          count=1, flags=re.M)
        assert n == 1, f"{name} not found in constants.py"
    CONSTANTS.write_text(text)
    edited = [f"line {k+1}" for k, p in enumerate(lines) if p is not None] + (["Bow A"] if v["bow"] else [])
    print(f"applied handles for: {', '.join(edited) or 'nothing (all formulas)'}; "
          f"right Bow A length={v.get('length')} -> {CONSTANTS}")


if __name__ == "__main__":
    {"export": lambda: export(), "apply": lambda: apply(sys.argv[2])}[sys.argv[1]]()
