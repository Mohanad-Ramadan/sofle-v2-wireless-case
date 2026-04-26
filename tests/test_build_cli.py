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
    stl = out / "sofle_case_left.stl"
    step = out / "sofle_case_left.step"
    assert stl.exists() and stl.stat().st_size > 1000
    assert step.exists() and step.stat().st_size > 1000
