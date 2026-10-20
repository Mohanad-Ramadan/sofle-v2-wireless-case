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
        cover = out / f"sofle_cover_{side}.stl"
        assert cover.stat().st_size > 1000

    assert sorted(path.name for path in out.iterdir()) == sorted(
        ("sofle_case_left.stl", "sofle_case_right.stl", "sofle_cover_left.stl", "sofle_cover_right.stl", unrelated.name)
    )


def _build(out, *args):
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build.py"), *args, "--out", str(out),
         "--tolerance", "0.01", "--angular-tolerance", "0.1"],
        check=True, cwd=str(ROOT), capture_output=True, text=True,
    ).stdout


def test_oled_modes_suffix_both_stls_and_print_the_fit_report(tmp_path):
    """Plan §4 / AC6 / AC7: right --oled long and left --oled short."""
    from sofle_case import constants as C

    right = _build(tmp_path, "right", "--oled", "long")
    left = _build(tmp_path, "left", "--oled", "short")
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted((
        "sofle_case_right_oled-long.stl", "sofle_cover_right_oled-long.stl",
        "sofle_case_left_oled-short.stl", "sofle_cover_left_oled-short.stl"))
    assert all(p.stat().st_size > 1000 for p in tmp_path.iterdir())

    def nets_line(side):
        nets = C.j3_nets(side)
        pads = C.oled_pads(side)
        return (f"  chosen pads: {','.join(map(str, pads))} "
                f"(nets {' '.join(nets[i] for i in pads)})")

    for out, side, mode in ((right, "right", "long"), (left, "left", "short")):
        lines = out.splitlines()
        assert f"OLED fit report: side={side} mode={mode} (physical frame, mm)" in lines
        assert "  height datum (PCB bottom Z): 9.100" in lines
        assert "  window minY - MCU minY: 6.095   (MCU minY 82.980)" in lines
        assert nets_line(side) in lines
        assert ("  module bottom vs jack/header-tail: UNCHECKED "
                "(measured top Z is authoritative)") in lines
        assert "  WARNING plug reach: cover face to jack face 3.385 (none: 0.720);" in out
        assert "cover north y: 121.465   tray outer north y: 123.465   north wall extra: 2.665" in out

    assert "  chosen pads: 0,1,2,3 (nets SDA SCL VCC GND)" in right
    assert "  chosen pads: 1,2,3,4 (nets GND VCC SCL SDA)" in left
    assert "  J3 pad x: 18.870 21.410 23.950 26.490 29.030" in right
    assert "  window x: 18.680..24.680  y: 89.075..111.455" in right
    assert "  window x: 124.580..130.580  y: 89.075..111.455" in left
    assert "  MCU board top z: 21.700   header-tail top z: 23.860" in right
    assert "  MCU board top z: 18.500   header-tail top z: 20.660" in left
    assert "  USB jack z: 20.700..23.860   cover USB port z: 20.200..24.360" in right
    assert "  USB jack z: 14.740..17.900   cover USB port z: 14.240..18.400" in left
    assert "  tray USB notch z: none" in right
    assert "  tray USB notch z: 13.940..15.700" in left
    assert "  ridge z: 27.400   ramp top y: 80.765   roof clearance over module: 0.600" in right
    assert "  ridge z: 24.200   ramp top y: 80.765   roof clearance over module: 0.600" in left
    assert "tray wall depth at port n/a" in right
    assert "tray wall depth at port 5.415..6.295" in left


def test_none_mode_keeps_unsuffixed_names_and_prints_no_report(tmp_path):
    out = _build(tmp_path, "right", "--oled", "none")
    assert "OLED fit report" not in out
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "sofle_case_right.stl", "sofle_cover_right.stl"]
