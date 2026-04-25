"""Tests for CPL parser."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_parse_cpl_extracts_known_components(tmp_path):
    out_dir = tmp_path / "data"
    out_dir.mkdir()
    csv = ROOT / "data" / "raw" / "CPL-SofleKeyboard.csv"
    script = ROOT / "scripts" / "parse_cpl.py"
    subprocess.run(
        [sys.executable, str(script), str(csv), "--out", str(out_dir)],
        check=True,
    )
    data = json.loads((out_dir / "components.json").read_text())

    # Spec §2.3 expected positions (PCB coords, mm). Tolerances per CPL precision.
    expected = {
        "U1":   (10.27, -16.16),    # MCU
        "SW31": (2.945, -43.23),    # slide switch
        "RSW1": (7.72,  -45.35),    # reset
        "SW25": (9.47,  -65.95),    # rotary encoder
        "J3":   (5.22,  -33.69),    # OLED socket
    }
    for des, (ex, ey) in expected.items():
        assert des in data, f"missing {des}"
        x, y = data[des]["x"], data[des]["y"]
        assert abs(x - ex) < 0.05, f"{des} X: {x} vs {ex}"
        assert abs(y - ey) < 0.05, f"{des} Y: {y} vs {ey}"
