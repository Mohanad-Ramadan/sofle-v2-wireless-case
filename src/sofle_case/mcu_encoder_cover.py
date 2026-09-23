"""Removable canopy over the MCU, slide switch, and encoder.

The shell starts at the coplanar switch-plate/case-rim datum. Two PCB screw
bosses and a short north lip extend below it; the lip follows the tray's
drafted rim with a calibrated seam. Geometry is built in right-half coordinates
and mirrored only after all side-specific openings have been cut.
"""
from __future__ import annotations

import math
from functools import cache
from typing import Literal, cast

from build123d import (
    Bezier,
    Box,
    BuildLine,
    BuildPart,
    BuildSketch,
    Face,
    Line,
    Location,
    Locations,
    Part,
    Plane,
    Polyline,
    Pos,
    Solid,
    extrude,
    fillet,
    loft,
    make_face,
    mirror,
)
from OCP.Standard import Standard_Failure

from . import constants as C
from . import tray as Tray
from .pcb_geometry import rotate_2d, slide_switch_placement
from .plate_geometry import load_plate_cutouts

Side = Literal["left", "right"]


@cache
def _north_landing_y() -> float:
    """The actual tray north rim, with a calibrated gap onto its draft."""
    outer_y = Tray._outer_extruded(0, 1).bounding_box().max.Y
    return outer_y - C.RIM_FACET_RUN + C.COVER_CHAMFER_GAP


def _mirror_left(part: Part) -> Part:
    return cast(Part, Pos(C.OUTER_WIDTH / 2, 0, 0) * mirror(
        Pos(-C.OUTER_WIDTH / 2, 0, 0) * part, about=Plane.YZ))


def _th_positions(side: Side = "right") -> list[tuple[float, float]]:
    points = [C.pcb_to_case(*point) for point in C.COVER_MOUNT_HOLES_PCB]
    if side == "left":
        return [(C.OUTER_WIDTH - x, y) for x, y in points]
    return points


def _cover_wall_x_y() -> tuple[float, float, float, float]:
    west = (C.pcb_to_case(0, 0)[0] - C.COVER_WALL_LANDING_OFFSET
            - C.COVER_WEST_OUTSET)
    east = 34.6
    north = _north_landing_y()
    _, enc_y, bbox_w, _ = _encoder_bbox()
    south_at_encoder = (enc_y - bbox_w/2 - C.COVER_ENCODER_CAVITY_CLEAR
                        - C.COVER_WALL_THICKNESS - 3.0)
    return west, east, north, south_at_encoder


def _knife_slope() -> float:
    """Slope of the tray's actual straightened south-west flare."""
    a, b = Tray._outer_poly_pts()[2:4]
    return (b[1] - a[1]) / (b[0] - a[0])


def _cover_outer_polygon() -> list[tuple[float, float]]:
    """Compact footprint whose min-Y edge is parallel to the tray SW flare."""
    west, east, north, south_at_encoder = _cover_wall_x_y()
    enc_x = C.pcb_to_case(*C.SW_ENCODER_POS)[0]
    slope = _knife_slope()
    south_w = south_at_encoder + slope * (west - enc_x)
    south_e = south_at_encoder + slope * (east - enc_x)
    return [(west, north), (east, north), (east, south_e), (west, south_w)]


def _cover_inner_polygon() -> list[tuple[float, float]]:
    west, east, north, south_at_encoder = _cover_wall_x_y()
    enc_x = C.pcb_to_case(*C.SW_ENCODER_POS)[0]
    slope = _knife_slope()
    iw, ie = west + C.COVER_WEST_WALL, east - C.COVER_EAST_WALL
    inward_y = C.COVER_WALL_THICKNESS * math.sqrt(1 + slope*slope)
    sw = south_at_encoder + slope * (iw - enc_x) + inward_y
    se = south_at_encoder + slope * (ie - enc_x) + inward_y
    return [(iw, north-C.COVER_NORTH_WALL),
            (ie, north-C.COVER_NORTH_WALL), (ie, se), (iw, sw)]


def _face(points: list[tuple[float, float]], north_radius: float = 0.0,
          south_radius: float = 0.0):
    """Polygon face with smooth transitions at the north and south rims."""
    with BuildSketch(Plane.XY) as sketch:
        with BuildLine():
            Polyline(*points, close=True)
        make_face()
        if north_radius:
            north = max(y for _, y in points)
            verts = [v for v in sketch.vertices() if abs(v.Y-north) < 0.05]
            try:
                fillet(verts, radius=north_radius)
            except (ValueError, Standard_Failure) as exc:
                raise RuntimeError("required canopy north-corner rounds failed") from exc
        if south_radius:
            south = sorted((v for v in sketch.vertices()), key=lambda v: v.Y)[:2]
            try:
                fillet(south, radius=south_radius)
            except (ValueError, Standard_Failure) as exc:
                raise RuntimeError("required canopy south-corner rounds failed") from exc
    return sketch.sketch.faces()[0]


def _cover_roof_z(y: float, side: Side) -> float:
    """Analytic cubic smoothstep roof with horizontal end tangents."""
    z0, z1 = C.COVER_FOOT_Z, C.cover_ridge_top_z(side)
    y0, y1 = C.COVER_RAMP_FOOT_Y, C.COVER_RAMP_TOP_Y
    if y <= y0:
        return z0
    if y >= y1:
        return z1
    t = (y-y0)/(y1-y0)
    return z0 + (z1-z0)*(3*t*t - 2*t*t*t)


def _encoder_bbox() -> tuple[float, float, float, float]:
    """Authoritative EC11 plate-window bbox, matched to SW_ENCODER_POS."""
    enc_x, enc_y = C.pcb_to_case(*C.SW_ENCODER_POS)
    for cutout in load_plate_cutouts():
        points = [C.pcb_to_case(x, y) for x, y in cutout]
        cx = sum(x for x, _ in points)/len(points)
        cy = sum(y for _, y in points)/len(points)
        if math.hypot(cx-enc_x, cy-enc_y) < 1.0:
            xs, ys = [x for x, _ in points], [y for _, y in points]
            return enc_x, enc_y, max(xs)-min(xs), max(ys)-min(ys)
    raise AssertionError("encoder cutout not found within 1 mm of SW_ENCODER_POS")


def _roof_above_cutter(side: Side, inner: bool, x_span: tuple[float, float],
                       y_span: tuple[float, float]) -> Part:
    """Space above one exact cubic Bezier roof, swept along X."""
    y0, y1 = C.COVER_RAMP_FOOT_Y, C.COVER_RAMP_TOP_Y
    thickness = C.COVER_TOP_THICKNESS if inner else 0.0
    z0 = C.COVER_FOOT_Z - thickness
    z1 = C.cover_ridge_top_z(side) - thickness
    length = y1-y0
    y_min, y_max = y_span
    ceiling = C.cover_ridge_top_z(side) + 8.0
    with BuildPart() as bp:
        with BuildSketch(Plane.YZ):
            with BuildLine():
                Line((y_max, ceiling), (y_max, z1))
                Line((y_max, z1), (y1, z1))
                Bezier((y1, z1), (y1-length/3, z1),
                       (y0+length/3, z0), (y0, z0))
                Line((y0, z0), (y_min, z0))
                Line((y_min, z0), (y_min, ceiling))
                Line((y_min, ceiling), (y_max, ceiling))
            make_face()
        extrude(amount=(x_span[1]-x_span[0])+4.0)
    assert bp.part is not None
    return cast(Part, Pos(x_span[0]-2.0, 0, 0) * bp.part)


def _north_shoulder_cutter(side: Side, x_span: tuple[float, float]) -> Part:
    """0.5 run / 1.0 drop facet, the tray rim's 2:1 drafted language."""
    north = max(y for _, y in _cover_outer_polygon())
    ridge = C.cover_ridge_top_z(side)
    run, drop = 0.5, 1.0
    with BuildPart() as bp:
        with BuildSketch(Plane.YZ):
            with BuildLine():
                Polyline((north-run, ridge), (north, ridge-drop),
                         (north, ridge+2), (north-run, ridge+2), close=True)
            make_face()
        extrude(amount=(x_span[1]-x_span[0])+2.0)
    assert bp.part is not None
    return cast(Part, Pos(x_span[0]-1.0, 0, 0) * bp.part)


def _shoulder_section(side: Side, scale: float, drop: float) -> Face:
    """YZ cutter section following the exact roof Bezier."""
    y0, y1 = C.COVER_RAMP_FOOT_Y, C.COVER_RAMP_TOP_Y
    z0, z1 = C.COVER_FOOT_Z, C.cover_ridge_top_z(side)
    length = y1-y0

    def lowered(y: float, z: float) -> tuple[float, float]:
        effective = min(drop, max(0.0, z-C.COVER_FOOT_Z))
        return y, z-scale*effective

    poles = [lowered(*p) for p in (
        (y0, z0), (y0+length/3, z0), (y1-length/3, z1), (y1, z1))]
    north = max(y for _, y in _cover_outer_polygon())
    ceiling = z1+4.0
    with BuildSketch(Plane.YZ) as sketch:
        with BuildLine():
            Bezier(*poles)
            Line(poles[-1], lowered(north, z1))
            Line(lowered(north, z1), (north, ceiling))
            Line((north, ceiling), (y0, ceiling))
            Line((y0, ceiling), poles[0])
        make_face()
    return cast(Face, sketch.sketch.faces()[0])


def _side_shoulder_cutter(side: Side, x_wall: float, east: bool) -> Part:
    """Ruled swept cutter for a 1.2 run / 2.4 drop side shoulder."""
    run, drop, pad = 1.2, 2.4, 1.0
    outside = x_wall+pad if east else x_wall-pad
    inside = x_wall-run if east else x_wall+run
    scale = (pad+run)/run
    sections = [Pos(outside, 0, 0)*_shoulder_section(side, scale, drop),
                Pos(inside, 0, 0)*_shoulder_section(side, 0.0, drop)]
    with BuildPart() as bp:
        loft(sections, ruled=True)
    assert bp.part is not None
    return cast(Part, bp.part)


def _shell(side: Side) -> Part:
    outer_pts, inner_pts = _cover_outer_polygon(), _cover_inner_polygon()
    x_span = (min(x for x, _ in outer_pts), max(x for x, _ in outer_pts))
    y_span = (min(y for _, y in outer_pts)-2, max(y for _, y in outer_pts)+2)
    h = C.cover_ridge_top_z(side) + 2 - C.MAIN_RIM_Z
    outer = cast(Part, Pos(0, 0, C.MAIN_RIM_Z) *
                 extrude(_face(outer_pts, C.COVER_CORNER_R, C.COVER_SOUTH_CORNER_R), amount=h))
    outer = cast(Part, outer - _roof_above_cutter(side, False, x_span, y_span))
    outer = cast(Part, outer - _north_shoulder_cutter(side, x_span))
    outer = cast(Part, outer-_side_shoulder_cutter(side, x_span[0], False)
                 - _side_shoulder_cutter(side, x_span[1], True))
    inner = cast(Part, Pos(0, 0, C.MAIN_RIM_Z-0.2) *
                 extrude(_face(inner_pts, max(0.2, C.COVER_CORNER_R-C.COVER_NORTH_WALL),
                               max(0.2, C.COVER_SOUTH_CORNER_R-C.COVER_WALL_THICKNESS)),
                         amount=h+0.4))
    inner = cast(Part, inner - _roof_above_cutter(side, True, x_span, y_span))
    return cast(Part, outer-inner)


def _north_chamfer_lip() -> Part:
    """Seat on the tray's 2:1 north draft, with a 0.2 mm printed seam."""
    west, east, north, _ = _cover_wall_x_y()
    z = C.MAIN_RIM_Z
    drop = 1.7
    run = drop * C.RIM_FACET_RUN / C.RIM_FACET_DROP
    # The inboard edge follows the real facet. The upper tip overlaps the
    # canopy north wall so the result remains one printable solid.
    with BuildPart() as lip:
        with BuildSketch(Plane.YZ):
            with BuildLine():
                Polyline((north-0.25, z+0.5), (north+0.65, z+0.5),
                         (north+run+0.65, z-drop),
                         (north+run, z-drop), close=True)
            make_face()
        extrude(amount=east-west-2.0)
    assert lip.part is not None
    return cast(Part, Pos(west+1.0, 0, 0) * lip.part)


def _boss(at: tuple[float, float], side: Side) -> Part:
    x, y = at
    top = _cover_roof_z(y, side) - C.COVER_TOP_THICKNESS + 0.2
    boss = Solid.make_cylinder(C.COVER_BOSS_OD/2, top-C.PCB_TOP_Z).translate((x, y, C.PCB_TOP_Z))
    straight = Solid.make_cylinder(C.COVER_BOSS_TAP_DIA/2,
                                   C.COVER_BOSS_BORE_DEPTH-C.COVER_BOSS_BORE_CHAMFER).translate(
                                       (x, y, C.PCB_TOP_Z+C.COVER_BOSS_BORE_CHAMFER))
    chamfer = Solid.make_cone(C.COVER_BOSS_TAP_DIA/2+C.COVER_BOSS_BORE_CHAMFER,
                              C.COVER_BOSS_TAP_DIA/2, C.COVER_BOSS_BORE_CHAMFER).translate(
                                  (x, y, C.PCB_TOP_Z))
    return cast(Part, boss-straight-chamfer)


def _rounded_bore(width: float, lo: float, hi: float, y0: float, y1: float) -> Part:
    cx = C.pcb_to_case(*C.MCU_POS)[0]
    bore = cast(Part, Solid.make_box(width, y1-y0, hi-lo).translate((cx-width/2, y0, lo)))
    radius = min(C.COVER_USB_PORT_R, (hi-lo)/2-1e-3, width/2-1e-3)
    axial = [e for e in bore.edges() if abs(e.tangent_at(0.5).Y) > 0.9]
    try:
        return cast(Part, fillet(axial, radius=radius))
    except (ValueError, Standard_Failure):
        return bore


def _usb_cutter(side: Side) -> Part:
    north = max(y for _, y in _cover_outer_polygon())
    lo, hi = C.cover_usb_port_z(side)
    return _rounded_bore(C.COVER_USB_PORT_W, lo, hi,
                         north-C.COVER_NORTH_WALL-1.0, north+2.0)


def _slide_actuator_cavity() -> Part:
    """Registered rotated can+nub footprint, grown by the structural pad."""
    cx, cy, rot = slide_switch_placement()
    offsets = [
        (C.SLIDE_ACTUATOR_PIN_CENTER_X, 0.0,
         C.SLIDE_ACTUATOR_BODY_L, C.SLIDE_ACTUATOR_BODY_W),
        (C.SLIDE_ACTUATOR_PIN_CENTER_X,
         -(C.SLIDE_ACTUATOR_BODY_W/2+C.SLIDE_ACTUATOR_NUB_D/2),
         C.SLIDE_ACTUATOR_NUB_L, C.SLIDE_ACTUATOR_NUB_D),
    ]
    z0 = C.PCB_TOP_Z-0.3
    z1 = C.MAIN_RIM_Z + 0.3
    pad = C.SLIDE_ACTUATOR_PAD
    with BuildPart() as cavity:
        for lx, ly, dx, dy in offsets:
            ox, oy = rotate_2d(lx, ly, rot)
            with Locations(Location((cx+ox, cy+oy, (z0+z1)/2), (0, 0, rot))):
                Box(dx+2*pad, dy+2*pad, z1-z0)
    assert cavity.part is not None
    return cast(Part, cavity.part)


def _slide_slot(side: Side) -> Part:
    """Small rounded access slot following the switch's rotated travel axis."""
    cx, cy, rot = slide_switch_placement()
    dx, dy = rotate_2d(
        C.SLIDE_ACTUATOR_PIN_CENTER_X,
        -(C.SLIDE_ACTUATOR_BODY_W / 2 + C.SLIDE_ACTUATOR_NUB_D / 2), rot)
    z0 = C.SLIDE_NUB_Z - C.SLIDE_ACTUATOR_NUB_H / 2 - C.COVER_NUB_PAD
    z1 = C.cover_ridge_top_z(side) + 2.0
    slot = cast(Part, Solid.make_box(C.COVER_SLIDE_SLOT_LENGTH,
                                    C.COVER_SLIDE_SLOT_WIDTH, z1-z0).translate(
                                        (-C.COVER_SLIDE_SLOT_LENGTH/2,
                                         -C.COVER_SLIDE_SLOT_WIDTH/2, z0)))
    vertical = [e for e in slot.edges() if abs(e.tangent_at(0.5).Z) > 0.9]
    slot = cast(Part, fillet(vertical, radius=C.COVER_SLIDE_SLOT_RADIUS))
    return cast(Part, Location((cx+dx, cy+dy, 0), (0, 0, rot)) * slot)


def _slide_cutter(side: Side) -> Part:
    return cast(Part, _slide_slot(side) + _slide_actuator_cavity())


def build_mcu_encoder_cover(side: Side = "right") -> Part:
    if side not in ("left", "right"):
        raise ValueError(f"side must be 'left' or 'right', got {side!r}")
    cover = cast(Part, _shell(side) + _north_chamfer_lip())
    for point in _th_positions("right"):
        cover = cast(Part, cover+_boss(point, side))
    cover = cast(Part, cover-_usb_cutter(side)-_slide_cutter(side))
    x, y, _, _ = _encoder_bbox()
    shaft = Solid.make_cylinder(C.COVER_SHAFT_CUTOUT_DIA/2, 10.0).translate(
        (x, y, C.COVER_FOOT_Z-C.COVER_TOP_THICKNESS-1.0))
    cover = cast(Part, cover-shaft)
    if side == "left":
        cover = _mirror_left(cover)
    return cover


if __name__ == "__main__":
    from ocp_vscode import show
    show(build_mcu_encoder_cover("right"), build_mcu_encoder_cover("left"),
         names=["cover_right", "cover_left"])
