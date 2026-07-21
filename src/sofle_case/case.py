"""Compose the full case half from tray + standoffs, minus the battery pocket.

Also splits that geometry into the sandwich clamshell: ``build_bottom_part`` and
``build_top_part`` cut the shell at ``SEAM_Z`` into two printable pieces that screw
together through the standoffs. See ``.omc/specs/deep-dive-sandwich-case-top-bottom.md``.
"""
from __future__ import annotations
from typing import Literal, cast
from build123d import Part, mirror, Plane, Pos, fillet, Axis, BuildPart, Locations, Cylinder, Sphere, Solid, Box, Location
from OCP.Standard import Standard_Failure
from OCP.ShapeFix import ShapeFix_Shape
from OCP.TopoDS import TopoDS
from . import constants as C
from .pcb_geometry import slide_switch_placement, rotate_2d
from .tray import build_tray
from .standoffs import stepped_standoff
from .battery import battery_pocket
from .top_cover import build_top_cover, _load_plate_cutouts
from .canopy import build_canopy, CANOPY_RIDGE_TOP_Z


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


def _encoder_bbox() -> tuple[float, float, float, float]:
    """Locate the EC11 encoder cutout and return (enc_cx, enc_cy, bbox_w, bbox_h)
    in case coords, matched by centroid proximity to SW_ENCODER_POS."""
    enc_cx, enc_cy = C.pcb_to_case(*C.SW_ENCODER_POS)
    matched = None
    for cut_pcb in _load_plate_cutouts():
        case_pts = [C.pcb_to_case(x, y) for x, y in cut_pcb]
        cx = sum(p[0] for p in case_pts) / len(case_pts)
        cy = sum(p[1] for p in case_pts) / len(case_pts)
        if ((cx - enc_cx) ** 2 + (cy - enc_cy) ** 2) ** 0.5 < 1.0:
            matched = case_pts
            break
    assert matched is not None, "encoder cutout not found within 1mm of SW_ENCODER_POS"
    xs = [p[0] for p in matched]
    ys = [p[1] for p in matched]
    bbox_w, bbox_h = max(xs) - min(xs), max(ys) - min(ys)
    assert 10 < bbox_w < 16 and 10 < bbox_h < 16, (
        f"encoder cutout bbox {bbox_w:.1f}x{bbox_h:.1f} outside expected 10-16mm range"
    )
    return enc_cx, enc_cy, bbox_w, bbox_h


def _encoder_shell() -> Part:
    """Single-body plateau over the EC11 encoder in the TOP part.

    One low mound centred on the encoder: hollow inside to clear the ~12 mm box
    that protrudes above the cover, a closed roof, and a plain shaft hole. It
    leaves the cover tangentially (concave ogee foot) and rounds over at the top
    edge, so it reads as a single plateau — not a two-tier bezel. The box is
    hidden; the bushing and 6 mm shaft exit through the ENCODER_SHAFT_HOLE_DIA hole.

    The base overlaps the cover membrane (starts at MAIN_RIM_Z) and the cavity is
    grown ENCODER_SHELL_CAVITY_CLEAR past the exact window so the ring bites into
    solid cover material for a robust fusion."""
    enc_cx, enc_cy, bbox_w, bbox_h = _encoder_bbox()

    clr = C.ENCODER_SHELL_CAVITY_CLEAR
    cav_w = bbox_w + 2 * clr
    cav_h = bbox_h + 2 * clr
    outer_w = cav_w + 2 * C.ENCODER_SHELL_WALL
    outer_h = cav_h + 2 * C.ENCODER_SHELL_WALL

    plateau_h = C.ENCODER_SHELL_TOP_Z - C.MAIN_RIM_Z
    outer = Solid.make_box(outer_w, outer_h, plateau_h).translate(
        (enc_cx - outer_w / 2, enc_cy - outer_h / 2, C.MAIN_RIM_Z)
    )

    # Lid-stub: a thin flange at the cover level (MAIN_RIM_Z → COVER_TOP_Z) that
    # gives the concave foot a clean local surface to roll onto, so the foot is
    # filleted HERE in the isolated shell instead of hunting it among the fused
    # lid's messy faces (fuse-margin, neighbour windows) where OCC can't blend it.
    # Once fused to the cover the stub is coplanar with the membrane and vanishes
    # into the lid; it is sized to stay clear of the neighbouring switch window.
    foot_margin = C.ENCODER_BEZEL_FOOT_R + 0.3
    stub_w = outer_w + 2 * foot_margin
    stub_h = outer_h + 2 * foot_margin
    stub = Solid.make_box(stub_w, stub_h, C.COVER_TOP_Z - C.MAIN_RIM_Z).translate(
        (enc_cx - stub_w / 2, enc_cy - stub_h / 2, C.MAIN_RIM_Z)
    )
    body = cast(Part, outer + stub)

    # Open cavity: from just below the membrane up to the roof underside (clears box).
    cav_z0 = C.MAIN_RIM_Z - 0.2
    cav_z1 = C.ENCODER_CAVITY_TOP_Z
    cavity = Solid.make_box(cav_w, cav_h, cav_z1 - cav_z0).translate(
        (enc_cx - cav_w / 2, enc_cy - cav_h / 2, cav_z0)
    )
    # Shaft hole through the roof.
    shaft = Solid.make_cylinder(
        C.ENCODER_SHAFT_HOLE_DIA / 2, C.ENCODER_SHELL_TOP_Z - cav_z1 + 0.4
    ).translate((enc_cx, enc_cy, cav_z1 - 0.2))

    shell = cast(Part, body - cavity - shaft)

    top_z = C.ENCODER_SHELL_TOP_Z

    # Round the vertical corners into arcs (rounded-rectangle plan).
    vert = [e for e in shell.edges()
            if abs(e.tangent_at(0.5).Z) > 0.9 and e.length > 2.0]
    if vert:
        try:
            shell = cast(Part, fillet(vert, radius=3.0))
        except (ValueError, Standard_Failure):
            pass

    def _near_plateau_wall(e) -> bool:
        """Edge on the plateau's outer wall loop (radial ≈ outer half), excluding
        the cavity/shaft (inner) and the stub (farther out)."""
        m = e.center()
        cheby = max(abs(m.X - enc_cx), abs(m.Y - enc_cy))
        return cav_w / 2 + 0.3 < cheby < outer_w / 2 + 0.5

    # Convex round-over of the plateau's top edge (roof ↔ outer wall).
    top_round = [e for e in shell.edges()
                 if abs(e.center().Z - top_z) < 0.2
                 and (e.bounding_box().max.Z - e.bounding_box().min.Z) < 0.3
                 and _near_plateau_wall(e)]
    if top_round:
        try:
            shell = cast(Part, fillet(top_round, radius=C.ENCODER_BEZEL_TOP_R))
        except (ValueError, Standard_Failure):
            pass

    # Concave foot: roll the plateau's outer wall into the lid-stub top at the
    # cover level (Z = COVER_TOP_Z), completing the tangent ogee.
    foot = [e for e in shell.edges()
            if abs(e.center().Z - C.COVER_TOP_Z) < 0.2
            and (e.bounding_box().max.Z - e.bounding_box().min.Z) < 0.3
            and _near_plateau_wall(e)]
    if foot:
        try:
            shell = cast(Part, fillet(foot, radius=C.ENCODER_BEZEL_FOOT_R))
        except (ValueError, Standard_Failure):
            pass

    # Soften the shaft-hole lip.
    lip = [e for e in shell.edges()
           if abs(e.center().Z - top_z) < 0.2
           and (e.bounding_box().max.Z - e.bounding_box().min.Z) < 0.3
           and max(abs(e.center().X - enc_cx),
                   abs(e.center().Y - enc_cy)) < C.ENCODER_SHAFT_HOLE_DIA / 2 + 0.5]
    if lip:
        try:
            shell = cast(Part, fillet(lip, radius=0.6))
        except (ValueError, Standard_Failure):
            pass

    return shell


def _slide_scoop() -> Part:
    """Wide, top-open 'decrement' scoop in the −X wall + canopy over the slide switch.

    A rounded valley WIDER in Y than tall in Z, cut from a floor just below the actuator nub UP
    through the upper wall and the whole canopy (roof included) — so it is open from the top and
    the −X side and a finger/nail reaches the SK12D07VG3 nub. ``build_top_part`` subtracts it
    AFTER the canopy is fused, lowering both the wall and the cover in one op. The floor is above
    ``SEAM_Z``, so it lives entirely in the TOP part (the BOTTOM is untouched — access is from the
    top/side, not from below). See the slide-switch section in ``constants.py``.

    Built as a tall box (floor → over the canopy ridge) through the full wall thickness, with its
    floor and plan corners rounded on the STANDALONE box (robust — not filleting a boolean)."""
    sw_cy = C.pcb_to_case(*C.SW_SLIDE_POS)[1]
    outer = C.pcb_to_case(0, 0)[0] - C.WALL_THICKNESS - C.PCB_XY_CLEARANCE   # −X outer wall face
    inner = C.pcb_to_case(0, 0)[0] - C.PCB_XY_CLEARANCE                       # inner wall face
    x0 = outer - 1.5 - C.SLIDE_SCOOP_X_SHIFT            # start outside the face (mouth fully open)
    x1 = inner + C.SLIDE_SCOOP_INNER_MARGIN - C.SLIDE_SCOOP_X_SHIFT   # just past the inner face → bares the nub
    y0, y1 = sw_cy - C.SLIDE_SCOOP_W / 2, sw_cy + C.SLIDE_SCOOP_W / 2
    z0 = C.SLIDE_SCOOP_FLOOR_Z
    z1 = CANOPY_RIDGE_TOP_Z + 2.0                       # above the roof → cuts through the canopy

    box = cast(Part, Solid.make_box(x1 - x0, y1 - y0, z1 - z0).translate((x0, y0, z0)))
    # Round the plan corners (vertical edges), then the floor edges — on the isolated box.
    vert = [e for e in box.edges() if abs(e.tangent_at(0.5).Z) > 0.9]
    try:
        box = cast(Part, fillet(vert, radius=C.SLIDE_SCOOP_SIDE_R))
    except (ValueError, Standard_Failure):
        pass
    floor = [e for e in box.edges() if e.bounding_box().max.Z < z0 + 0.05]
    try:
        box = cast(Part, fillet(floor, radius=C.SLIDE_SCOOP_FLOOR_R))
    except (ValueError, Standard_Failure):
        pass
    return box


def _slide_actuator_cavity() -> Part:
    """Drop-in clearance pocket shaped to the SK12D07VG3 slide switch (TOP part).

    A single rectangular prism = the switch's combined can+nub footprint grown by
    ``SLIDE_ACTUATOR_PAD`` on every X/Y face, poured from ``SLIDE_ACTUATOR_FLOOR_Z``
    (the seam) up to ``SLIDE_ACTUATOR_TOP_Z`` (the cover underside). Subtracting it in
    ``build_top_part`` carves a registered channel the switch drops straight down into,
    clearing the lower −X wall the actuator nub sweeps through. There is NO retaining
    lip (a plain clearance pocket), and the top is capped at the cover underside so the
    1.0 mm lid is never perforated. Clearance inboard of the inner wall face just cuts
    air (harmless) — keeping the cutter a simple prism.

    The footprint tracks the switch exactly: it is derived from the SW31 placement
    (``slide_switch_placement`` → components.json + ``pcb_to_case`` + rotation, the same
    registration ``_slide_switch_body`` uses) and the OWNED structural can/nub dims in
    ``constants.py`` — no phantom internals are imported. See the slide-switch actuator
    container section in ``constants.py``."""
    cx, cy, rot = slide_switch_placement()

    # Combined can+nub footprint, built with the SAME placement/rotation math the
    # phantom body uses (can centred over the pin span; nub protruding local −Y),
    # then bounding-boxed to a plan rectangle. Z here is a throwaway unit height —
    # the pocket's real Z span is set below from FLOOR_Z→TOP_Z.
    bdx, bdy = rotate_2d(C.SLIDE_ACTUATOR_PIN_CENTER_X, 0.0, rot)
    ndx, ndy = rotate_2d(
        C.SLIDE_ACTUATOR_PIN_CENTER_X,
        -(C.SLIDE_ACTUATOR_BODY_W / 2 + C.SLIDE_ACTUATOR_NUB_D / 2),
        rot,
    )
    with BuildPart() as bp:
        with Locations(Location((cx + bdx, cy + bdy, 0.0), (0, 0, rot))):
            Box(C.SLIDE_ACTUATOR_BODY_L, C.SLIDE_ACTUATOR_BODY_W, 1.0)
        with Locations(Location((cx + ndx, cy + ndy, 0.0), (0, 0, rot))):
            Box(C.SLIDE_ACTUATOR_NUB_L, C.SLIDE_ACTUATOR_NUB_D, 1.0)
    assert bp.part is not None
    fp = bp.part.bounding_box()

    pad = C.SLIDE_ACTUATOR_PAD
    x0, x1 = fp.min.X - pad, fp.max.X + pad
    y0, y1 = fp.min.Y - pad, fp.max.Y + pad
    z0, z1 = C.SLIDE_ACTUATOR_FLOOR_Z, C.SLIDE_ACTUATOR_TOP_Z

    return cast(Part, Solid.make_box(x1 - x0, y1 - y0, z1 - z0).translate((x0, y0, z0)))


def build_top_part(side: Side) -> Part:
    """TOP clamshell half: upper walls (``SEAM_Z → COVER_TOP_Z``) + switch membrane.

    The full-height shell is clipped to the above-seam slab, then the plate-shaped
    membrane (from ``top_cover``) is fused on as the ceiling. The membrane already
    carries its switch windows, open MCU/OLED/JST bay and M2 clearance holes; it is
    grown by ``COVER_FUSE_MARGIN`` so it bites into the upper walls and the whole TOP
    is one solid. Standoffs are NOT part of the TOP — they live in the BOTTOM and
    pass up through the open cavity.

    The bay canopy is FUSED on here (``build_canopy``): its ramp grows out of the cover
    surface and merges into it (its base overlaps the cover for a clean union), so the MCU
    hood is integral to the TOP — not a separate part.

    Finally two −X cuts carve the slide switch: the wide finger ``_slide_scoop`` (tray look)
    and then the ``_slide_actuator_cavity`` (a switch-shaped drop-in pocket poured to the
    seam). Both floors sit at/above ``SEAM_Z`` so the BOTTOM part is untouched."""
    if side not in ("left", "right"):
        raise ValueError(f"side must be 'left' or 'right', got {side!r}")

    top = _clip_z(build_tray(rim_z=C.COVER_TOP_Z), C.SEAM_Z, C.COVER_TOP_Z + 1.0)
    top = cast(Part, top + build_top_cover(fuse_margin=C.COVER_FUSE_MARGIN))
    top = cast(Part, top + _encoder_shell())
    top = cast(Part, top + build_canopy())
    # Slide-switch finger scoop: cut AFTER the canopy fuse so it lowers the wall + cover together.
    top = cast(Part, top - _slide_scoop())
    # Slide-switch drop-in pocket: registered switch-shaped cavity poured to the seam.
    top = cast(Part, top - _slide_actuator_cavity())
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

    # The bay canopy is now FUSED into build_top_part, so it shows as part of "top". The MCU
    # block is grouped UNDER the "top" node as its own hideable child ("mcu"), so you can toggle
    # it off in the OCP tree and inspect the bay / canopy interior beneath it.
    from build123d import Compound
    from sofle_case.pcb_phantom import _mcu_block

    top_body = build_top_part(_SIDE)
    top_body.label = "top_part"
    mcu = _mirror_part(_mcu_block())   # phantoms are right-half; mirror to match the shown side
    mcu.label = "mcu"
    top_group = Compound(children=[top_body, mcu])
    top_group.label = "top"

    parts = [build_bottom_part(_SIDE), top_group]
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
