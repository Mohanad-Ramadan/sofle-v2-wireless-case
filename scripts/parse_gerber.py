"""Parse SofleKeyboard EdgeCuts GERBER + PTH drill into JSON.

Usage:
    python scripts/parse_gerber.py <edgecuts.gbr> <pth.drl> [--out data/]
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path
from collections import defaultdict
import click


# ---------- GERBER ----------

_FS_RE = re.compile(r"%FSLAX(\d)(\d)Y(\d)(\d)\*%")
_COORD_RE = re.compile(r"X(-?\d+)Y(-?\d+)D0([12])\*")


def _parse_format(text: str) -> tuple[int, int]:
    m = _FS_RE.search(text)
    if not m:
        raise ValueError("missing %FSLAX...% format spec")
    return int(m.group(1)), int(m.group(2))  # int_digits, frac_digits


def _decode(raw: int, frac: int) -> float:
    return raw / (10 ** frac)


def parse_edgecuts(gbr_path: Path) -> list[tuple[float, float]]:
    """Return ordered closed polygon as list of (x,y) in mm; first==last."""
    text = gbr_path.read_text()
    _, frac = _parse_format(text)

    segments: list[tuple[tuple[float, float], tuple[float, float]]] = []
    cur: tuple[float, float] | None = None

    for m in _COORD_RE.finditer(text):
        x = round(_decode(int(m.group(1)), frac), 4)
        y = round(_decode(int(m.group(2)), frac), 4)
        op = m.group(3)
        if op == "2":  # pen-up move
            cur = (x, y)
        elif op == "1":  # draw line
            if cur is None:
                raise ValueError("D01 before any D02")
            segments.append((cur, (x, y)))
            cur = (x, y)

    if not segments:
        raise ValueError("no segments parsed from gerber")

    # Build adjacency, then walk one closed loop.
    adj: dict[tuple[float, float], list[tuple[float, float]]] = defaultdict(list)
    for a, b in segments:
        adj[a].append(b)
        adj[b].append(a)

    start = segments[0][0]
    loop = [start]
    prev = None
    cur_pt = start
    while True:
        nbrs = [p for p in adj[cur_pt] if p != prev]
        if not nbrs:
            raise ValueError(f"dead-end at {cur_pt}")
        nxt = nbrs[0]
        loop.append(nxt)
        if nxt == start:
            break
        prev, cur_pt = cur_pt, nxt
        if len(loop) > len(segments) + 2:
            raise ValueError("loop walk exceeded segment count")

    return loop


# ---------- Excellon drill ----------

_TOOL_RE = re.compile(r"^T(\d+)C([\d.]+)")
_DRILL_COORD_RE = re.compile(r"^X(-?[\d.]+)Y(-?[\d.]+)")
_TOOL_SEL_RE = re.compile(r"^T(\d+)\s*$")


def parse_pth_holes(drl_path: Path, target_dia_mm: float = 4.1) -> list[tuple[float, float]]:
    """Return list of (x,y) in mm for the drill tool matching target_dia_mm.

    The drill file may use INCH units; this function auto-detects and converts.
    """
    # Detect units from header
    header = drl_path.read_text()
    inch_mode = bool(re.search(r"^\s*INCH\b", header, re.MULTILINE))
    unit_mult = 25.4 if inch_mode else 1.0  # convert to mm

    target_tool: str | None = None
    tools: dict[str, float] = {}
    holes: list[tuple[float, float]] = []
    cur_tool: str | None = None

    for line in header.splitlines():
        line = line.strip()
        m = _TOOL_RE.match(line)
        if m:
            dia_in_file_units = float(m.group(2))
            dia_mm = dia_in_file_units * unit_mult
            tools[m.group(1)] = dia_mm
            if abs(dia_mm - target_dia_mm) < 0.05:
                target_tool = m.group(1)
            continue
        m = _TOOL_SEL_RE.match(line)
        if m:
            cur_tool = m.group(1)
            continue
        m = _DRILL_COORD_RE.match(line)
        if m and cur_tool == target_tool:
            x = float(m.group(1)) * unit_mult
            y = float(m.group(2)) * unit_mult
            holes.append((round(x, 3), round(y, 3)))

    if target_tool is None:
        raise ValueError(f"no tool with Ø{target_dia_mm}mm found (tools: {tools})")
    return holes


@click.command()
@click.argument("gbr", type=click.Path(exists=True, path_type=Path))
@click.argument("drl", type=click.Path(exists=True, path_type=Path))
@click.option("--out", "out_dir", type=click.Path(path_type=Path),
              default=Path("data"), show_default=True)
def main(gbr: Path, drl: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    polygon = parse_edgecuts(gbr)
    holes = parse_pth_holes(drl, target_dia_mm=4.1)

    (out_dir / "pcb_outline.json").write_text(json.dumps(polygon, indent=2))
    (out_dir / "mounting_holes.json").write_text(json.dumps(holes, indent=2))

    bbox = (min(p[0] for p in polygon), min(p[1] for p in polygon),
            max(p[0] for p in polygon), max(p[1] for p in polygon))
    click.echo(f"polygon: {len(polygon)} vertices, bbox={bbox}")
    click.echo(f"holes:   {len(holes)} @ Ø{4.1}mm")


if __name__ == "__main__":
    main()
