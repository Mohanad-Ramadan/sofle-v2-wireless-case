"""Parse the original Sofle v2 top-plate **gerber** Edge_Cuts → plate_outline.json
+ plate_cutouts.json (PCB coords).

This supersedes parse_kicad_plate.py for the real hardware: the authoritative
v2 gerber (v2-gerber-top.zip) has 29 standard 14 mm MX switch cutouts + the
encoder window, whereas the older KiCad-derived data carried wrong 18.36 mm
openings.

Gerber → PCB transform (derived by matching the plate outline bbox, which is
exactly the PCB span 143.5 × 115.5 mm, to the PCB coordinate range; verified to
land the 14 mm cutout centres on the components.json switch positions within
~0.7 mm, and the X offset matches parse_kicad_plate's _KX_OFF):

    pcb_x = gerber_x - 27.132
    pcb_y = gerber_y + 31.431

Usage:
    python scripts/parse_plate_gerber.py <top_plate-Edge_Cuts.gbr> [--out data/]
"""
from __future__ import annotations
import json
import re
from collections import defaultdict
from pathlib import Path

import click

# %FSLAX46Y46*% → 6 decimal places, leading zeros omitted, absolute, mm.
_COORD_RE = re.compile(r"X(-?\d+)Y(-?\d+)D0([12])\*")
_SCALE = 1e6

# Gerber board coords → repo PCB coords (see module docstring).
_DX = -27.132
_DY = 31.431


def _gerber_to_pcb(gx: float, gy: float) -> tuple[float, float]:
    return (round(gx + _DX, 3), round(gy + _DY, 3))


def _parse_segments(text: str) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """Each D02 (move) followed by D01 (draw) is one edge segment."""
    segs: list[tuple[tuple[float, float], tuple[float, float]]] = []
    cur: tuple[float, float] | None = None
    for m in _COORD_RE.finditer(text):
        p = (round(int(m.group(1)) / _SCALE, 4), round(int(m.group(2)) / _SCALE, 4))
        if m.group(3) == "2":          # move
            cur = p
        else:                          # draw
            if cur is not None and cur != p:
                segs.append((cur, p))
            cur = p
    return segs


def _walk_polygons(segs: list[tuple[tuple, tuple]]) -> list[list[tuple]]:
    """Walk the segment adjacency graph into ordered vertex loops."""
    adj: dict[tuple, list[tuple]] = defaultdict(list)
    for s, e in segs:
        adj[s].append(e)
        adj[e].append(s)

    visited: set[tuple] = set()
    polygons: list[list[tuple]] = []
    for start in list(adj):
        if start in visited:
            continue
        poly = [start]
        visited.add(start)
        prev: tuple | None = None
        cur = start
        while True:
            choices = [p for p in adj[cur] if p != prev and p not in visited]
            if not choices:
                break
            nxt = choices[0]
            poly.append(nxt)
            visited.add(nxt)
            prev, cur = cur, nxt
        if len(poly) >= 3:
            polygons.append(poly)
    return polygons


def _signed_area(pts: list[tuple]) -> float:
    n = len(pts)
    return abs(sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1]
                   for i in range(n))) / 2.0


def parse_plate(gerber_path: Path) -> tuple[list, list]:
    """Return (outer_polygon_closed, [cutout_polygon, ...]) in PCB coords."""
    polys = _walk_polygons(_parse_segments(gerber_path.read_text()))
    polys_pcb = [[_gerber_to_pcb(x, y) for x, y in poly] for poly in polys]
    polys_pcb.sort(key=_signed_area, reverse=True)
    outer = polys_pcb[0] + [polys_pcb[0][0]]   # close it (first == last)
    cutouts = polys_pcb[1:]
    return outer, cutouts


@click.command()
@click.argument("edge_cuts_gbr", type=click.Path(exists=True, path_type=Path))
@click.option("--out", "out_dir", type=click.Path(path_type=Path),
              default=Path("data"), show_default=True)
def main(edge_cuts_gbr: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    outer, cutouts = parse_plate(edge_cuts_gbr)

    (out_dir / "plate_outline.json").write_text(json.dumps(outer, indent=2))
    (out_dir / "plate_cutouts.json").write_text(json.dumps(cutouts, indent=2))

    click.echo(f"plate outline: {len(outer)} vertices (closed)")
    click.echo(f"switch/encoder cutouts: {len(cutouts)}")
    for i, c in enumerate(cutouts):
        xs = [p[0] for p in c]
        ys = [p[1] for p in c]
        click.echo(f"  [{i:2d}] {len(c)}-gon  {max(xs) - min(xs):.2f} x {max(ys) - min(ys):.2f} mm")


if __name__ == "__main__":
    main()
