"""Removable canopy over the MCU, slide switch, and encoder.

The shell starts at the coplanar switch-plate/case-rim datum. Only the two PCB
screw bosses extend below it. Geometry is built in right-half
coordinates and mirrored after all side-specific openings have been cut.
"""
from __future__ import annotations

import math
from collections.abc import Callable
from functools import cache
from itertools import pairwise
from typing import Literal, cast

from build123d import (
    Bezier,
    BuildLine,
    BuildPart,
    BuildSketch,
    Face,
    Line,
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
from . import cover_mark
from . import tray as Tray
from .plate_geometry import load_plate_cutouts
from .slide_access import slide_body_cavity, slide_finger_cutout

Side = Literal["left", "right"]
Point = tuple[float, float]


@cache
def _north_landing_y() -> float:
    """Local straight MCU-wall rim, clear of the more northerly relief bump."""
    mcu_x = C.pcb_to_case(*C.MCU_POS)[0]
    points = Tray._outer_poly_pts()
    segments = zip(points, points[1:] + points[:1])
    local_y = max(a[1] for a, b in segments
                  if abs(a[1]-b[1]) < 1e-6 and min(a[0], b[0]) <= mcu_x <= max(a[0], b[0]))
    return (local_y + C.WALL_THICKNESS + C.PCB_XY_CLEARANCE
            - C.RIM_FACET_RUN)


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
    _, enc_y, _, bbox_h = _encoder_bbox()
    south = (enc_y - bbox_h/2 - C.COVER_ENCODER_CAVITY_CLEAR
             - C.COVER_SOUTH_WALL_THICKNESS - C.COVER_RECESS_DEPTH)
    return west, east, north, south


def _cover_polygon(*, west_inset: float = 0.0, east_inset: float = 0.0,
                   north_inset: float = 0.0, south_inset: float = 0.0
                   ) -> list[tuple[float, float]]:
    """Offset every south facet normally, preserving thickness through the recess."""
    west, east, north, south = _cover_wall_x_y()
    west, east = west+west_inset, east-east_inset
    north, south = north-north_inset, south+south_inset
    enc_x = C.pcb_to_case(*C.SW_ENCODER_POS)[0]
    depth = C.COVER_RECESS_DEPTH
    half, flat = C.COVER_RECESS_HALF_WIDTH, C.COVER_RECESS_FLAT_HALF_WIDTH
    slope = depth/(half-flat)
    shift = south_inset*slope/(math.hypot(slope, 1)+1)
    # A wider side wall can make its cavity corner clip redundant.
    clip_e = max(0.0, C.COVER_SOUTH_CORNER_CLIP-east_inset
                 + south_inset*(math.sqrt(2)-1))
    clip_w = max(0.0, C.COVER_SOUTH_CORNER_CLIP-west_inset
                 + south_inset*(math.sqrt(2)-1))
    points = [(west, north), (east, north), (east, south+clip_e)]
    if clip_e:
        points.append((east-clip_e, south))
    points.extend(((enc_x+half+shift, south), (enc_x+flat+shift, south+depth),
                   (enc_x-flat-shift, south+depth), (enc_x-half-shift, south),
                   (west+clip_w, south)))
    if clip_w:
        points.append((west, south+clip_w))
    return points


def _cover_outer_polygon() -> list[tuple[float, float]]:
    return _cover_polygon()


def _cover_inner_polygon() -> list[tuple[float, float]]:
    return _cover_polygon(west_inset=C.COVER_WEST_WALL, east_inset=C.COVER_EAST_WALL,
                          north_inset=C.COVER_NORTH_WALL,
                          south_inset=C.COVER_SOUTH_WALL_THICKNESS)


def _face(points: list[tuple[float, float]], north_radius: float = 0.0):
    """Faceted south outline with the existing rounded north corners."""
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
                       y_span: tuple[float, float], *, drop: float | None = None) -> Part:
    """Space above one exact cubic Bezier roof, swept along X.

    ``drop`` lowers the whole roof vertically (used for the groove floor)."""
    y0, y1 = C.COVER_RAMP_FOOT_Y, C.COVER_RAMP_TOP_Y
    if drop is not None:
        thickness = drop
    else:
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


def _side_shoulder_cutter(side: Side, x_wall: float, east: bool) -> Part:
    """One ruled Bezier surface rotates from the south bevel into the side draft."""
    y0, y1 = C.COVER_RAMP_FOOT_Y, C.COVER_RAMP_TOP_Y
    z0, z1 = C.COVER_FOOT_Z, C.cover_ridge_top_z(side)
    bevel = C.COVER_SOUTH_BEVEL
    run, drop = C.COVER_SIDE_CHAMFER_RUN, C.COVER_SIDE_CHAMFER_DROP
    inward = -1 if east else 1
    # Repeated end values give zero longitudinal derivatives at both junctions.
    ys = (y0, y0+(y1-y0)/3, y1-(y1-y0)/3, y1)
    zs = (z0, z0, z1, z1)
    runs, drops = (bevel, bevel, run, run), (bevel, bevel, drop, drop)
    outer = [(x_wall, y, z-d) for y, z, d in zip(ys, zs, drops)]
    inner = [(x_wall+inward*r, y, z) for y, z, r in zip(ys, zs, runs)]
    ramp_face = Face.make_bezier_surface([outer, inner])
    north = _north_landing_y()
    ridge_face = Face.make_bezier_surface([
        [outer[-1], (x_wall, north, z1-drop)],
        [inner[-1], (x_wall+inward*run, north, z1)],
    ])
    direction = (0, 0, z1+4)
    return cast(Part, Solid.extrude(ramp_face, direction)+Solid.extrude(ridge_face, direction))


def _shell(side: Side) -> Part:
    outer_pts, inner_pts = _cover_outer_polygon(), _cover_inner_polygon()
    x_span = (min(x for x, _ in outer_pts), max(x for x, _ in outer_pts))
    y_span = (min(y for _, y in outer_pts)-2, max(y for _, y in outer_pts)+2)
    h = C.cover_ridge_top_z(side) + 2 - C.MAIN_RIM_Z
    outer_face = _face(outer_pts, C.COVER_CORNER_R)
    outer = cast(Part, Pos(0, 0, C.MAIN_RIM_Z) * extrude(outer_face, amount=h))
    outer = cast(Part, outer - _roof_above_cutter(side, False, x_span, y_span))
    outer = cast(Part, outer - _north_shoulder_cutter(side, x_span))
    outer = cast(Part, outer-_side_shoulder_cutter(side, x_span[0], False)
                 - _side_shoulder_cutter(side, x_span[1], True))
    # Wrap the bevel around the low canopy; the side cutters continue it up the ramp.
    bevel = C.COVER_SOUTH_BEVEL
    top_face = _face(_cover_polygon(west_inset=bevel, east_inset=bevel,
                                    south_inset=bevel), C.COVER_CORNER_R)
    bevel_z = C.COVER_FOOT_Z-bevel
    bevel_slice = Pos(0, 0, bevel_z) * extrude(outer_face, amount=bevel)
    retained = loft([Pos(0, 0, bevel_z)*outer_face,
                     Pos(0, 0, C.COVER_FOOT_Z)*top_face], ruled=True)
    low_canopy = Solid.make_box(x_span[1]-x_span[0]+2, C.COVER_RAMP_FOOT_Y-y_span[0],
                               bevel+2).translate((x_span[0]-1, y_span[0], bevel_z-1))
    outer = cast(Part, outer-((bevel_slice-retained) & low_canopy))
    inner = cast(Part, Pos(0, 0, C.MAIN_RIM_Z-0.2) *
                 extrude(_face(inner_pts, 0.2), amount=h+0.4))
    inner = cast(Part, inner - _roof_above_cutter(side, True, x_span, y_span))
    return cast(Part, outer-inner)


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


def _mark_inside(side: Side) -> Callable[[Point], bool]:
    """Canonical-frame test for where the connection mark's centreline may run.

    Like the old canopy marks, strokes run ``COVER_MARK_RUN_OUT`` past the outline: the groove
    holds its depth to the chamfer's top line, then dies as the chamfer drops away beneath the
    lowered-roof floor. Only the encoder shaft margin and the USB opening are kept clear."""
    half = max(C.COVER_MARK_WIDTH, C.COVER_MARK_CURVE_WIDTH)/2
    outer = _cover_outer_polygon()
    run = C.COVER_MARK_RUN_OUT
    x0, x1 = min(x for x, _ in outer)-run, max(x for x, _ in outer)+run
    y0, y1 = min(y for _, y in outer)-run, max(y for _, y in outer)+run
    ex, ey, _, _ = _encoder_bbox()
    quiet = C.COVER_SHAFT_CUTOUT_DIA/2+C.COVER_MARK_QUIET_R+half
    mcu_x = C.pcb_to_case(*C.MCU_POS)[0]
    usb_half = C.COVER_USB_PORT_W/2+1.0+half
    usb_y = max(y for _, y in outer)-C.COVER_NORTH_WALL-1.0-half

    def inside(p: Point) -> bool:
        x, y = p
        if not (x0 <= x <= x1 and y0 <= y <= y1):
            return False
        if math.dist(p, (ex, ey)) <= quiet:
            return False
        return not (abs(x-mcu_x) < usb_half and y > usb_y)

    return inside


def _turn_radius(a: Point, b: Point, c: Point) -> float:
    """Circumradius of three consecutive stroke vertices; a fold shows as a small radius."""
    twice_area = abs((b[0]-a[0])*(c[1]-a[1])-(c[0]-a[0])*(b[1]-a[1]))
    if twice_area < 1e-12:
        return math.inf
    return math.dist(a, b)*math.dist(b, c)*math.dist(a, c)/(2*twice_area)


def _band_prism(points: list[Point], width: float, z0: float, z1: float) -> Part:
    """Flat-floored groove: a planar band along one polyline, extruded z0 to z1."""
    half = width/2
    normals = []
    for a, b in pairwise(points):
        length = math.dist(a, b)
        normals.append((-(b[1]-a[1])/length, (b[0]-a[0])/length))
    left: list[Point] = []
    right: list[Point] = []
    for i, p in enumerate(points):
        if i in (0, len(points)-1):
            n, scale = normals[0 if i == 0 else -1], 1.0
        else:
            assert _turn_radius(points[i-1], p, points[i+1]) > width, (
                "connection mark stroke folds on itself")
            prev, nxt = normals[i-1], normals[i]
            m = (prev[0]+nxt[0], prev[1]+nxt[1])
            size = math.hypot(*m)
            n = (m[0]/size, m[1]/size)
            scale = 1.0/(n[0]*prev[0]+n[1]*prev[1])
        ox, oy = n[0]*half*scale, n[1]*half*scale
        left.append((p[0]+ox, p[1]+oy))
        right.append((p[0]-ox, p[1]-oy))
    face = _face(left+right[::-1])
    return cast(Part, Pos(0, 0, z0) * extrude(face, amount=z1-z0))


def _mark_cutter(side: Side) -> Part:
    """M17-3 grooves for one cover, in canonical (built, pre-mirror) coordinates."""
    outer = _cover_outer_polygon()
    xs, ys = [x for x, _ in outer], [y for _, y in outer]
    x_span = (min(xs), max(xs))
    y_span = (min(ys)-2, max(ys)+2)
    # Start below the open underside so no groove face is coplanar with it.
    z0, z1 = C.MAIN_RIM_Z-1.0, C.cover_ridge_top_z(side)+2.0
    grooves: Part | None = None
    for points, width in cover_mark.strokes(side, _mark_inside(side)):
        band = _band_prism(points, width, z0, z1)
        grooves = band if grooves is None else cast(Part, grooves+band)
    assert grooves is not None, "connection mark produced no strokes"
    floor = _roof_above_cutter(side, False, x_span, y_span, drop=C.COVER_MARK_DEPTH)
    return cast(Part, grooves & floor)


def build_mcu_encoder_cover(side: Side = "right", mark: bool = C.COVER_MARK_ENABLED) -> Part:
    if side not in ("left", "right"):
        raise ValueError(f"side must be 'left' or 'right', got {side!r}")
    cover = _shell(side)
    if mark:
        cover = cast(Part, cover-_mark_cutter(side))
    for point in _th_positions("right"):
        cover = cast(Part, cover+_boss(point, side))
    cover = cast(Part, cover-_usb_cutter(side)-slide_finger_cutout()
                 - slide_body_cavity(C.MAIN_RIM_Z + 0.3))
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
