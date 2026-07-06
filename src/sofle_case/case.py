"""Compose the full case half from tray + standoffs, minus the battery pocket."""
from __future__ import annotations
from typing import Literal, cast
from build123d import Part, mirror, Plane, Pos, fillet, Axis, BuildPart, Locations, Cylinder, Sphere
from OCP.ShapeFix import ShapeFix_Shape
from OCP.TopoDS import TopoDS
from . import constants as C
from .tray import build_tray
from .standoffs import stepped_standoff
from .battery import battery_pocket


Side = Literal["left", "right"]


def _heal(part: Part) -> Part:
    """Repair face orientation after a reflection.

    Mirroring a solid that carries filleted top-rim blend surfaces yields a
    BRepCheck ``UnorientableShape`` — OCC's orientation bookkeeping fails on the
    reflected BSpline blends even though a mirror is an isometry and the shape
    is geometrically sound. ShapeFix_Shape flips the offending orientation flags
    without altering geometry (volume and bbox are preserved). Only the mirrored
    (left) half needs this; the right half is already valid."""
    fixer = ShapeFix_Shape(part.wrapped)
    fixer.Perform()
    fixed = fixer.Shape()
    return Part(TopoDS.Solid_s(fixed)) if fixed.ShapeType() == 2 else Part(fixed)


def build_case_half(side: Side) -> Part:
    """Build a single case half.

    ``side="right"`` returns the as-built geometry (MCU hill on the −X wall).
    ``side="left"`` returns the mirror image, reflected about the case
    centreline (X = OUTER_WIDTH / 2), so the MCU hill lands on the +X wall.
    """
    if side not in ("left", "right"):
        raise ValueError(f"side must be 'left' or 'right', got {side!r}")

    shell = build_tray()

    for hx, hy in C.MOUNTING_HOLES:
        cx, cy = C.pcb_to_case(hx, hy)
        shell += stepped_standoff(at=(cx, cy))

    shell = cast(Part, shell)

    shell -= battery_pocket()

    shell = cast(Part, shell)

    if side == "left":
        # Mirror about the YZ plane through case centre X = OUTER_WIDTH/2.
        # build123d's mirror() reflects about a plane through the origin, so we
        # shift by -OUTER_WIDTH/2, mirror about YZ, then shift back.
        shell = Pos(-C.OUTER_WIDTH / 2, 0, 0) * shell
        shell = mirror(shell, about=Plane.YZ)
        shell = Pos(C.OUTER_WIDTH / 2, 0, 0) * shell
        shell = cast(Part, shell)
        # Reflection leaves filleted rim blends unorientable; heal orientation
        # (geometry unchanged) so the half passes BRepCheck. See _heal().
        shell = _heal(shell)

    if not isinstance(shell, Part):
        solids = shell.solids()
        shell = Part(children=list(solids)) if solids else Part(children=[shell])

    return shell


# %%
def _corner_markers() -> Part:
    """Debug spheres at geometry transition points. All coords currently commented
    out — uncomment specific entries to visualise edges in the OCP viewer."""
    coords: tuple[tuple[float, float, float], ...] = (
        
    )
    with BuildPart() as bp:
        for x, y, z in coords:
            with Locations((x, y, z)):
                Sphere(radius=1.0)
    return bp.part # type: ignore


# %%
if __name__ == "__main__":
    from ocp_vscode import show
    from sofle_case.case import build_case_half
    from sofle_case import constants as C

    _SIDE: Side = "right"

    def _mirror_part(p: Part) -> Part:
        """Apply the same mirror transform as build_case_half() for side='left'.

        Phantoms are always built in right-half (un-mirrored) coordinates. When
        viewing the left half the same shift-mirror-shift must be applied so
        they stay aligned with the case geometry.
        """
        if _SIDE == "left":
            p = cast(Part, Pos(-C.OUTER_WIDTH / 2, 0, 0) * p)
            p = cast(Part, mirror(p, about=Plane.YZ))
            p = cast(Part, Pos(C.OUTER_WIDTH / 2, 0, 0) * p)
        return p

    parts = [build_case_half(_SIDE)]
    names = ["case"]

    if C.SHOW_PCB_PHANTOM:
        from sofle_case.pcb_phantom import build_pcb_phantom
        parts.append(_mirror_part(build_pcb_phantom()))
        names.append("pcb_phantom")

    if C.SHOW_PLATE_PHANTOM:
        from sofle_case.plate_phantom import build_plate_phantom
        parts.append(_mirror_part(build_plate_phantom()))
        names.append("plate_phantom")

    if C.SHOW_SWITCH_PHANTOM:
        from sofle_case.switch_phantom import build_switch_phantom
        parts.append(_mirror_part(build_switch_phantom()))
        names.append("switch_phantom")

    parts.append(_corner_markers())
    names.append("corner_markers")

    show(*parts, names=names)
