"""CLI: build a Sofle sandwich case half and export STL + STEP (+ optional PNG).

Each half is a clamshell of two printable parts — a BOTTOM (floor + lower walls +
standoffs + battery pocket) and a TOP (upper walls + switch membrane + encoder
plateau) — that screw together through the standoffs at the seam.

Usage:
    python scripts/build.py right
    python scripts/build.py left --out output/
    python scripts/build.py right --show          # open in OCP CAD Viewer
    python scripts/build.py right --legacy         # also export the old single-piece tray
"""
from __future__ import annotations
from pathlib import Path
from typing import cast
import click
from build123d import Part, export_stl, export_step
from sofle_case.case import build_top_part, build_bottom_part, build_case_half, Side


def _export(part: Part, stem: Path) -> None:
    stl, step = stem.with_suffix(".stl"), stem.with_suffix(".step")
    if not export_stl(part, str(stl)):
        raise RuntimeError(f"export_stl failed for {stl}")
    if not export_step(part, str(step)):
        raise RuntimeError(f"export_step failed for {step}")
    click.echo(f"  wrote {stl} ({stl.stat().st_size} bytes)")
    click.echo(f"  wrote {step} ({step.stat().st_size} bytes)")


@click.command()
@click.argument("side", type=click.Choice(["left", "right"]))
@click.option("--out", "out_dir", type=click.Path(path_type=Path),
              default=Path("output"), show_default=True)
@click.option("--show", "show_viewer", is_flag=True, default=False,
              help="Open the built parts in OCP CAD Viewer after building.")
@click.option("--png", "export_png", is_flag=True, default=False,
              help="Screenshot the model to a PNG via OCP CAD Viewer (viewer must be running).")
@click.option("--legacy", "build_legacy", is_flag=True, default=False,
              help="Also export the legacy single-piece tray (build_case_half).")
def main(side: str, out_dir: Path, show_viewer: bool, export_png: bool,
         build_legacy: bool) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    s = cast(Side, side)

    click.echo(f"building {side} TOP part...")
    top = build_top_part(s)
    _export(top, out_dir / f"sofle_{side}_top")

    click.echo(f"building {side} BOTTOM part...")
    bottom = build_bottom_part(s)
    _export(bottom, out_dir / f"sofle_{side}_bottom")

    parts = [top, bottom]
    names = [f"{side}_top", f"{side}_bottom"]

    if build_legacy:
        click.echo(f"building {side} legacy single-piece tray...")
        legacy = build_case_half(s)
        _export(legacy, out_dir / f"sofle_case_{side}")
        parts.append(legacy)
        names.append(f"{side}_legacy")

    if show_viewer or export_png:
        from ocp_vscode import show
        show(*parts, names=names)

    if export_png:
        import time
        from ocp_vscode import save_screenshot
        png_path = out_dir / f"sofle_{side}.png"
        time.sleep(1.0)  # let the viewer finish rendering before screenshotting
        save_screenshot(str(png_path.absolute()))
        if png_path.exists():
            click.echo(f"  wrote {png_path} ({png_path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
