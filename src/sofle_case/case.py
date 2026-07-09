"""Compose the full case half from tray + standoffs, minus the battery pocket.

Also splits that geometry into the sandwich clamshell: ``build_bottom_part`` and
``build_top_part`` cut the shell at ``SEAM_Z`` into two printable pieces that screw
together through the standoffs. See ``.omc/specs/deep-dive-sandwich-case-top-bottom.md``.
"""
from __future__ import annotations
from typing import Literal, cast
from build123d import Part, mirror, Plane, Pos, fillet, Axis, BuildPart, Locations, Cylinder, Sphere, Solid
from OCP.ShapeFix import ShapeFix_Shape
from OCP.TopoDS import TopoDS
from . import constants as C
from .tray import build_tray
from .standoffs import stepped_standoff
from .battery import battery_pocket
from .top_cover import build_top_cover


Side = Literal["left", "right"]


def _as_part(shape) -> Part:
    """Normalise a boolean result to a single ``Part`` (mirrors build_tray's tail)."""
    if isinstance(shape, Part):
        return shape
    solids = shape.solids()
    return Part(children=list(solids)) if solids else Part(children=[shape])


def _clip_z(part: Part, z_lo: float, z_hi: float) -> Part:
    """Planar butt-cut: keep only the slab of ``part`` between z_lo and z_hi.

    Intersects with an oversized box so the cut face is exactly planar at the seam
    (guaranteeing mating faces between the two halves). The box overhangs the XY
    footprint generously so only the Z planes clip."""
    pad = 20.0
    box = Solid.make_box(
        C.OUTER_WIDTH + 2 * pad, C.OUTER_DEPTH + 2 * pad, z_hi - z_lo
    ).translate((-pad, -pad, z_lo))
    return _as_part(part & box)


def _mirror_left(part: Part) -> Part:
    """Reflect a right-half part onto the left half (about X = OUTER_WIDTH/2) + heal.

    build123d's mirror() reflects about a plane through the origin, so we shift by
    -OUTER_WIDTH/2, mirror about YZ, then shift back. The reflection leaves filleted
    rim blends unorientable; _heal fixes orientation (geometry unchanged)."""
    part = cast(Part, Pos(-C.OUTER_WIDTH / 2, 0, 0) * part)
    part = cast(Part, mirror(part, about=Plane.YZ))
    part = cast(Part, Pos(C.OUTER_WIDTH / 2, 0, 0) * part)
    return _heal(part)


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

    shell = _as_part(shell)

    if side == "left":
        shell = _mirror_left(shell)

    return shell


def build_bottom_part(side: Side) -> Part:
    """BOTTOM clamshell half: the shell clipped to ``0 → SEAM_Z`` plus full standoffs.

    The upper walls are cut away at the seam, leaving the floor + lower walls +
    battery pocket + bottom elephant-foot chamfer. The standoffs are added AFTER the
    clip so they keep their full height and protrude past the seam into the TOP's
    interior — the TOP clamps down onto their tap tops via the join screws."""
    if side not in ("left", "right"):
        raise ValueError(f"side must be 'left' or 'right', got {side!r}")

    # Build the full-height shell (walls to COVER_TOP_Z) so its seam face is planar
    # and identical to the TOP part's, then keep only the below-seam slab.
    bottom = _clip_z(build_tray(rim_z=C.COVER_TOP_Z), -1.0, C.SEAM_Z)

    for hx, hy in C.MOUNTING_HOLES:
        cx, cy = C.pcb_to_case(hx, hy)
        bottom = cast(Part, bottom + stepped_standoff(at=(cx, cy)))

    bottom = cast(Part, bottom - battery_pocket())
    bottom = _as_part(bottom)

    if side == "left":
        bottom = _mirror_left(bottom)

    return bottom


def build_top_part(side: Side) -> Part:
    """TOP clamshell half: upper walls (``SEAM_Z → COVER_TOP_Z``) + switch membrane.

    The full-height shell is clipped to the above-seam slab, then the plate-shaped
    membrane (from ``top_cover``) is fused on as the ceiling. The membrane already
    carries its switch windows, open MCU/OLED/JST bay and M2 clearance holes; it is
    grown by ``COVER_FUSE_MARGIN`` so it bites into the upper walls and the whole TOP
    is one solid. Standoffs are NOT part of the TOP — they live in the BOTTOM and
    pass up through the open cavity."""
    if side not in ("left", "right"):
        raise ValueError(f"side must be 'left' or 'right', got {side!r}")

    top = _clip_z(build_tray(rim_z=C.COVER_TOP_Z), C.SEAM_Z, C.COVER_TOP_Z + 1.0)
    top = cast(Part, top + build_top_cover(fuse_margin=C.COVER_FUSE_MARGIN))
    top = _as_part(top)

    if side == "left":
        top = _mirror_left(top)

    return top


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
    from sofle_case.case import build_bottom_part, build_top_part
    from sofle_case import constants as C

    _SIDE: Side = "right"

    def _mirror_part(p: Part) -> Part:
        """Apply the same mirror transform as the part builders for side='left'.

        Phantoms are always built in right-half (un-mirrored) coordinates. When
        viewing the left half the same shift-mirror-shift must be applied so
        they stay aligned with the case geometry.
        """
        if _SIDE == "left":
            p = cast(Part, Pos(-C.OUTER_WIDTH / 2, 0, 0) * p)
            p = cast(Part, mirror(p, about=Plane.YZ))
            p = cast(Part, Pos(C.OUTER_WIDTH / 2, 0, 0) * p)
        return p

    parts = [build_bottom_part(_SIDE), build_top_part(_SIDE)]
    names = ["bottom", "top"]

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

    # The switch membrane is now fused into build_top_part(), so the standalone
    # top_cover is not shown here (it would overlap the TOP part's ceiling).

    parts.append(_corner_markers())
    names.append("corner_markers")

    show(*parts, names=names)
