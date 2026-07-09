"""CLI: build a Sofle case half and export STL + STEP (+ optional PNG).

Usage:
    python scripts/build.py left
    python scripts/build.py right --out output/
    python scripts/build.py right --png          # requires OCP CAD Viewer running
"""
from __future__ import annotations
from pathlib import Path
from typing import cast
import click
from build123d import export_stl, export_step
from sofle_case.case import build_case_half, Side


@click.command()
@click.argument("side", type=click.Choice(["left", "right"]))
@click.option("--out", "out_dir", type=click.Path(path_type=Path),
              default=Path("output"), show_default=True)
@click.option("--show", "show_viewer", is_flag=True, default=False,
              help="Open result in OCP CAD Viewer after building.")
@click.option("--png", "export_png", is_flag=True, default=False,
              help="Screenshot the model to a PNG via OCP CAD Viewer (viewer must be running).")
@click.option("--cover", "build_cover", is_flag=True, default=False,
              help="Also export the top cover (sandwich lid). Single part, shared by both halves.")
def main(side: str, out_dir: Path, show_viewer: bool, export_png: bool, build_cover: bool) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    click.echo(f"building {side} half...")
    part = build_case_half(cast(Side, side))

    stl_path = out_dir / f"sofle_case_{side}.stl"
    step_path = out_dir / f"sofle_case_{side}.step"
    if not export_stl(part, str(stl_path)):
        raise RuntimeError(f"export_stl failed for {stl_path}")
    if not export_step(part, str(step_path)):
        raise RuntimeError(f"export_step failed for {step_path}")

    click.echo(f"  wrote {stl_path} ({stl_path.stat().st_size} bytes)")
    click.echo(f"  wrote {step_path} ({step_path.stat().st_size} bytes)")

    cover = None
    if build_cover:
        from sofle_case.top_cover import build_top_cover
        click.echo("building top cover...")
        cover = build_top_cover()
        cover_stl = out_dir / "sofle_top_cover.stl"
        cover_step = out_dir / "sofle_top_cover.step"
        if not export_stl(cover, str(cover_stl)):
            raise RuntimeError(f"export_stl failed for {cover_stl}")
        if not export_step(cover, str(cover_step)):
            raise RuntimeError(f"export_step failed for {cover_step}")
        click.echo(f"  wrote {cover_stl} ({cover_stl.stat().st_size} bytes)")
        click.echo(f"  wrote {cover_step} ({cover_step.stat().st_size} bytes)")

    if show_viewer or export_png:
        from ocp_vscode import show
        parts = [part] + ([cover] if cover is not None else [])
        names = [f"sofle_case_{side}"] + (["top_cover"] if cover is not None else [])
        show(*parts, names=names)

    if export_png:
        import time
        from ocp_vscode import save_screenshot
        png_path = out_dir / f"sofle_case_{side}.png"
        time.sleep(1.0)  # let the viewer finish rendering before screenshotting
        save_screenshot(str(png_path.absolute()))
        if png_path.exists():
            click.echo(f"  wrote {png_path} ({png_path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
