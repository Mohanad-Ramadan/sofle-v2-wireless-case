"""CLI: build one surface-less monolithic Sofle case half and export STL.

Usage:
    python scripts/build.py right
    python scripts/build.py left --out output/
    python scripts/build.py right --show          # open in OCP CAD Viewer
"""
from __future__ import annotations

from pathlib import Path
from typing import cast

import click
from build123d import Part, export_stl

from sofle_case.case import Side, build_case_half


def _remove_legacy_outputs(out_dir: Path, side: str) -> None:
    """Remove only known artifacts from the pre-monolithic build layout."""
    legacy_names = (
        f"sofle_case_{side}.step",
        f"sofle_{side}_top.stl",
        f"sofle_{side}_top.step",
        f"sofle_{side}_bottom.stl",
        f"sofle_{side}_bottom.step",
    )
    for name in legacy_names:
        path = out_dir / name
        if path.exists():
            path.unlink()
            click.echo(f"  removed legacy artifact {path}")


def _export(part: Part, stem: Path, tolerance: float = 1e-3, angular_tolerance: float = 0.05) -> None:
    stl = stem.with_suffix(".stl")
    # Keep a tighter angular tolerance than build123d's default so drafted
    # facets remain visually clean in the exported mesh.
    if not export_stl(part, str(stl), tolerance=tolerance, angular_tolerance=angular_tolerance):
        raise RuntimeError(f"export_stl failed for {stl}")
    click.echo(f"  wrote {stl} ({stl.stat().st_size} bytes)")


@click.command()
@click.argument("side", type=click.Choice(["left", "right"]))
@click.option("--out", "out_dir", type=click.Path(path_type=Path),
              default=Path("output"), show_default=True)
@click.option("--show", "show_viewer", is_flag=True, default=False,
              help="Open the built geometry in OCP CAD Viewer after building.")
@click.option("--phantoms", "show_phantoms", is_flag=True, default=False,
              help="Include hardware phantoms when viewing. Phantoms are never exported or fused.")
@click.option("--tolerance", type=float, default=1e-3, show_default=True,
              help="STL linear deflection (mm). Lower = finer, larger file.")
@click.option("--angular-tolerance", type=float, default=0.05, show_default=True,
              help="STL angular deflection (rad). Lower = smoother ramp, larger file. Default 0.05≈2.9° vs build123d 0.1≈5.7°.")
def main(side: str, out_dir: Path, show_viewer: bool, show_phantoms: bool,
         tolerance: float, angular_tolerance: float) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    _remove_legacy_outputs(out_dir, side)
    s = cast(Side, side)

    click.echo(f"building {side} monolithic case... (tol={tolerance} ang={angular_tolerance})")
    case = build_case_half(s)
    _export(case, out_dir / f"sofle_case_{side}", tolerance=tolerance, angular_tolerance=angular_tolerance)

    parts = [case]
    names = [f"{side}_case"]

    if show_phantoms:
        # View-only hardware. Built here rather than inside the case builders so nothing can
        # accidentally fuse a phantom into a printed part.
        from sofle_case import knob as K
        from sofle_case.pcb_phantom import build_pcb_phantom
        from sofle_case.plate_phantom import build_plate_phantom
        from sofle_case.switch_phantom import build_switch_phantom
        click.echo("building phantoms (view only)...")
        click.echo(f"  {K.knob_seating_report()}")
        def _side(part):
            """Every phantom is authored in RIGHT-hand coords, like the case itself; the left half
            is the mirror of the right, so phantoms get mirrored with it or they land on the wrong
            half. (The EC11 rides inside the PCB phantom and is mirrored along with it.)"""
            if side != "left":
                return part
            from build123d import Plane, Pos, mirror

            from sofle_case import constants as C
            return Pos(C.OUTER_WIDTH / 2, 0, 0) * mirror(
                Pos(-C.OUTER_WIDTH / 2, 0, 0) * part, about=Plane.YZ)

        for name, part in (("pcb+encoder+knob", _side(build_pcb_phantom(s))),
                           ("plate", _side(build_plate_phantom())),
                           ("switches", _side(build_switch_phantom())),
                           ("knob_on_untrimmed_shaft", _side(K.place_knob(bottomed=True)))):
            parts.append(part)
            names.append(f"{side}_{name}")

    if show_viewer:
        from viewer_guard import (
            require_live_viewer,  # scripts/ is on sys.path as this file's dir
        )
        port = require_live_viewer()
        from ocp_vscode import show
        show(*parts, names=names)
        click.echo(f"sent to the OCP viewer on port {port}")

if __name__ == "__main__":
    main()
