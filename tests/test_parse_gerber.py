"""Tests for GERBER + drill parsers."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_parse_gerber_produces_outline_and_holes(tmp_path):
    """Parser must emit pcb_outline.json (closed polygon) and mounting_holes.json (5 entries)."""
    out_dir = tmp_path / "data"
    out_dir.mkdir()
    gbr = ROOT / "data" / "raw" / "SofleKeyboard-EdgeCuts.gbr"
    drl = ROOT / "data" / "raw" / "SofleKeyboard-PTH.drl"
    assert gbr.exists() and drl.exists()

    script = ROOT / "scripts" / "parse_gerber.py"
    subprocess.run(
        [sys.executable, str(script), str(gbr), str(drl), "--out", str(out_dir)],
        check=True,
    )

    outline = json.loads((out_dir / "pcb_outline.json").read_text())
    holes = json.loads((out_dir / "mounting_holes.json").read_text())

    assert isinstance(outline, list)
    assert len(outline) >= 6  # PCB outline has at least 6 vertices
    assert outline[0] == outline[-1], "polygon must be closed (first == last)"

    # Bbox check (per spec §2.1) — all coords in mm
    xs = [p[0] for p in outline]
    ys = [p[1] for p in outline]
    assert abs(min(xs) - (-8.5)) < 0.05
    assert abs(max(xs) - 135.0) < 0.05
    assert abs(min(ys) - (-110.5)) < 0.05
    assert abs(max(ys) - 5.0) < 0.05

    assert len(holes) == 5
    expected = {
        (14.07, -80.26),
        (39.57, -19.05),
        (39.57, -56.96),
        (116.07, -25.66),
        (116.07, -63.96),
    }
    got = {(round(x, 2), round(y, 2)) for x, y in holes}
    assert got == expected
