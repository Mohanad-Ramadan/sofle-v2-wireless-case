"""Smoke test the build CLI; verify STL + STEP files are written."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_left_writes_outputs(tmp_path):
    out = tmp_path / "output"
    out.mkdir()
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build.py"),
         "left", "--out", str(out)],
        check=True, cwd=str(ROOT),
    )
    # The CLI builds the sandwich clamshell: a TOP and a BOTTOM part per side.
    for part in ("top", "bottom"):
        stl = out / f"sofle_left_{part}.stl"
        step = out / f"sofle_left_{part}.step"
        assert stl.exists() and stl.stat().st_size > 1000, f"missing {stl}"
        assert step.exists() and step.stat().st_size > 1000, f"missing {step}"


def test_build_legacy_flag_writes_single_piece(tmp_path):
    out = tmp_path / "output"
    out.mkdir()
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build.py"),
         "right", "--out", str(out), "--legacy"],
        check=True, cwd=str(ROOT),
    )
    stl = out / "sofle_case_right.stl"
    assert stl.exists() and stl.stat().st_size > 1000, f"missing {stl}"
