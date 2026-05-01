"""Parse top_plate.kicad_pcb Edge.Cuts → plate_outline.json + plate_cutouts.json.

Usage:
    python scripts/parse_kicad_plate.py <top_plate.kicad_pcb> [--out data/]
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from collections import defaultdict
import click

_LINE_RE = re.compile(
    r'\(gr_line\s+\(start\s+([-\d.]+)\s+([-\d.]+)\)\s+\(end\s+([-\d.]+)\s+([-\d.]+)\)\s+\(layer\s+Edge\.Cuts\)'
)

# KiCad page coords → PCB coords:  pcb_x = kx - KX_OFF;  pcb_y = KY_OFF - ky  (Y flip)
# Derived from KiCad (105.130898, 26.432072) == PCB (78.0, 5.0).
_KX_OFF = 27.1309
_KY_OFF = 31.432072


def _kicad_to_pcb(kx: float, ky: float) -> tuple[float, float]:
    return (round(kx - _KX_OFF, 3), round(_KY_OFF - ky, 3))


def _parse_segs(text: str) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    segs: list[tuple[tuple[float, float], tuple[float, float]]] = []
    for m in _LINE_RE.finditer(text):
        sx, sy = round(float(m.group(1)), 4), round(float(m.group(2)), 4)
        ex, ey = round(float(m.group(3)), 4), round(float(m.group(4)), 4)
        if abs(sx - ex) > 1e-4 or abs(sy - ey) > 1e-4:
            segs.append(((sx, sy), (ex, ey)))
    return segs


def _walk_polygons(segs: list[tuple[tuple, tuple]]) -> list[list[tuple]]:
    """Walk the segment adjacency graph to build ordered vertex lists per polygon."""
    adj: dict[tuple, list[tuple]] = defaultdict(list)
    for s, e in segs:
        adj[s].append(e)
        adj[e].append(s)

    visited: set[tuple] = set()
    polygons: list[list[tuple]] = []

    for start in list(adj):
        if start in visited:
            continue
        poly: list[tuple] = [start]
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
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += pts[i][0] * pts[j][1] - pts[j][0] * pts[i][1]
    return area / 2.0


def _remove_collinear(pts: list[tuple]) -> list[tuple]:
    n = len(pts)
    result = []
    for i in range(n):
        a = pts[(i - 1) % n]
        b = pts[i]
        c = pts[(i + 1) % n]
        cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if abs(cross) > 1e-3:
            result.append(b)
    return result


def parse_plate(kicad_path: Path) -> tuple[list, list]:
    """Return (outer_polygon_closed, [cutout_polygon, ...]) in PCB coords."""
    text = kicad_path.read_text()
    segs_kicad = _parse_segs(text)
    polys_kicad = _walk_polygons(segs_kicad)

    polys_pcb = []
    for poly in polys_kicad:
        pcb = [_kicad_to_pcb(kx, ky) for kx, ky in poly]
        pcb = _remove_collinear(pcb)
        polys_pcb.append(pcb)

    polys_pcb.sort(key=lambda p: abs(_signed_area(p)), reverse=True)
    outer = polys_pcb[0] + [polys_pcb[0][0]]  # close it (first == last)
    cutouts = polys_pcb[1:]
    return outer, cutouts


@click.command()
@click.argument("kicad_pcb", type=click.Path(exists=True, path_type=Path))
@click.option("--out", "out_dir", type=click.Path(path_type=Path),
              default=Path("data"), show_default=True)
def main(kicad_pcb: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    outer, cutouts = parse_plate(kicad_pcb)

    (out_dir / "plate_outline.json").write_text(json.dumps(outer, indent=2))
    (out_dir / "plate_cutouts.json").write_text(json.dumps(cutouts, indent=2))

    click.echo(f"plate outline: {len(outer)} vertices (closed)")
    click.echo(f"switch cutouts: {len(cutouts)}")
    for i, c in enumerate(cutouts):
        click.echo(f"  [{i:2d}] {len(c)}-gon  area={abs(_signed_area(c)):.2f} mm²")


if __name__ == "__main__":
    main()
