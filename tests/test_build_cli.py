"""Verify CLI cleanup of legacy outputs and exact per-side artifact handling."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_sides_clean_legacy_outputs_and_preserve_unrelated_files(tmp_path):
    out = tmp_path / "output"
    out.mkdir()
    stale_by_side = {}
    for side in ("left", "right"):
        stale_names = (
            f"sofle_case_{side}.step",
            f"sofle_{side}_top.stl",
            f"sofle_{side}_top.step",
            f"sofle_{side}_bottom.stl",
            f"sofle_{side}_bottom.step",
        )
        stale_by_side[side] = stale_names
        for name in stale_names:
            (out / name).write_bytes(b"legacy")
    unrelated = out / "keep-me.txt"
    unrelated.write_text("user file")

    for side in ("left", "right"):
        assert all((out / name).exists() for name in stale_by_side["right"])
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "build.py"), side, "--out", str(out)],
            check=True, cwd=str(ROOT), capture_output=True, text=True,
        )
        assert result.stdout.strip()
        artifact = out / f"sofle_case_{side}.stl"
        assert artifact.stat().st_size > 1000
        assert not any((out / name).exists() for name in stale_by_side[side])
        if side == "left":
            assert all((out / name).exists() for name in stale_by_side["right"])
        assert unrelated.exists()
        assert unrelated.read_text() == "user file"

    assert sorted(path.name for path in out.iterdir()) == sorted(
        ("sofle_case_left.stl", "sofle_case_right.stl", unrelated.name)
    )
