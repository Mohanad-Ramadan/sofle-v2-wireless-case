"""Compose the full case half from tray + standoffs, minus the battery pocket.

Also splits that geometry into the sandwich clamshell. The split is NOT a mid-wall
butt seam: ``build_top_part`` is a deep TUB that owns the full outer skin (wall
unbroken to the ground — no seam on any outer face), and ``build_bottom_part`` is a
thin INSET floor plate that joins via a rabbet (stepped lap) behind the skin. The two
still screw together through the same standoffs. See
``.omc/specs/deep-dive-sandwich-seam-modification.md``.
"""
from __future__ import annotations
import math
from functools import cache
from typing import Literal, cast
from build123d import (Part, mirror, Plane, Pos, fillet, chamfer, Axis, BuildPart,
                       BuildSketch, BuildLine, Line, Spline, Locations, Cylinder,
                       Sphere, Solid, Box, Location, GeomType, add, extrude, make_face)
from OCP.Standard import Standard_Failure
from OCP.ShapeFix import ShapeFix_Shape
from OCP.TopoDS import TopoDS
from . import constants as C
from .pcb_geometry import slide_switch_placement, rotate_2d
from .tray import build_tray, offset_extruded
from .standoffs import stepped_standoff
from .battery import battery_pocket
from .top_cover import build_top_cover, _load_plate_cutouts
from .canopy import build_canopy, usb_port_cutter, CANOPY_RIDGE_TOP_Z


Side = Literal["left", "right"]


def _as_part(shape) -> Part:
    """Normalise a boolean result to a single ``Part`` (mirrors build_tray's tail)."""
    if isinstance(shape, Part):
        return shape
    solids = shape.solids()
    return Part(children=list(solids)) if solids else Part(children=[shape])


def _plate_envelope() -> Part:
    """The BOTTOM inset floor plate body (no standoffs / battery pocket yet).

    A slab from ``Z 0 → SEAM_LEDGE_Z`` whose outer edge is a concentric offset of
    the PCB polygon, inset from the outer skin by ``SEAM_SKIN`` (so it tucks behind
    the tub's descending skin). Its outer face lands at polygon offset
    ``PCB_XY_CLEARANCE + SEAM_RIM_THK`` — i.e. the rim reaches from the cavity wall
    out through ``SEAM_RIM_THK`` of the wall, stopping ``SEAM_SKIN + SEAM_FIT_CLEAR``
    short of the outer face. A 45° ``SEAM_LEAD_IN`` chamfer on the rim's top-outer
    edge self-guides it into the tub skirt on assembly."""
    rim_outer = C.PCB_XY_CLEARANCE + C.SEAM_RIM_THK
    plate = offset_extruded(rim_outer, 0.0, C.SEAM_LEDGE_Z)
    # Lead-in chamfer: the plate is a plain prism, so every top edge is the outer
    # rim perimeter. Fall back on smaller legs, then none, rather than aborting.
    top_edges = plate.edges().filter_by_position(
        Axis.Z, minimum=C.SEAM_LEDGE_Z - 0.01, maximum=C.SEAM_LEDGE_Z + 0.01
    )
    for length in (C.SEAM_LEAD_IN, C.SEAM_LEAD_IN * 0.5):
        try:
            plate = cast(Part, chamfer(top_edges, length=length))
            break
        except (ValueError, Standard_Failure):
            continue
    return plate


def _plate_pocket() -> Part:
    """Cutter carving the inset plate pocket into the base of the TOP tub.

    The plate envelope grown by ``SEAM_FIT_CLEAR`` radially (so the seated plate has
    that clearance per side) and by ``SEAM_LEDGE_CLEAR`` in Z at the top (so the rim
    top clears the ledge and the screws, not the rabbet, set the clamp). Subtracting
    it from the full-height tray removes the floor + inner-wall material inboard of
    the skin below the ledge, automatically leaving the ``SEAM_SKIN`` skirt running
    to the ground. Starts below Z=0 so it clears the bottom face cleanly."""
    pocket_outer = C.PCB_XY_CLEARANCE + C.SEAM_RIM_THK + C.SEAM_FIT_CLEAR
    return offset_extruded(
        pocket_outer, -0.5, C.SEAM_LEDGE_Z + C.SEAM_LEDGE_CLEAR
    )


def _chamfer_pocket_mouth(part: Part) -> Part:
    """45° starter chamfer on the tub pocket MOUTH (the pocket's inner edge at Z≈0).

    The plate rim already has its own ``SEAM_LEAD_IN`` starter; this gives the mating
    tub side one too, so the plate self-guides into the pocket AND the mouth cannot
    elephant-foot-pinch on the first layers. The mouth is told apart from the outer
    bottom edge (already counter-chamfered) by a radial probe: at the pocket mouth the
    skin lies OUTWARD and air (the pocket) lies INWARD — the reverse of the outer edge.
    Runs on the invisible underside, so a size fallback / no-op is harmless (mirrors
    the ``_chamfer_outer_top_edges`` idiom)."""
    cx, cy = C.OUTER_WIDTH / 2, C.OUTER_DEPTH / 2

    def _solid(x: float, y: float, z: float) -> bool:
        probe = Solid.make_box(0.4, 0.4, 0.4).translate((x - 0.2, y - 0.2, z - 0.2))
        return cast(float, (part & probe).volume) > 1e-6

    mouth = []
    for e in part.edges():
        bb = e.bounding_box()
        if bb.max.Z - bb.min.Z > 0.05:          # horizontal edges only
            continue
        if not (-0.1 <= bb.min.Z <= 0.1):        # at the mouth plane (Z≈0)
            continue
        m = e.position_at(0.5)
        dx, dy = m.X - cx, m.Y - cy
        n = (dx * dx + dy * dy) ** 0.5
        if n < 1e-6:
            continue
        ux, uy = dx / n, dy / n
        # pocket mouth: skin OUTWARD, air INWARD (opposite of the outer bottom edge)
        if _solid(m.X + ux * 0.6, m.Y + uy * 0.6, 0.3) and not _solid(
                m.X - ux * 0.6, m.Y - uy * 0.6, 0.3):
            mouth.append(e)
    if not mouth:
        return part
    for length in (C.SEAM_POCKET_LEAD_IN, C.SEAM_POCKET_LEAD_IN * 0.5):
        try:
            return cast(Part, chamfer(mouth, length=length))
        except (ValueError, Standard_Failure):
            continue
    return part


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


# ---------------------------------------------------------------------------
# Integrated tent wedge (BOTTOM case)
# ---------------------------------------------------------------------------

def tent_plane() -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """``(origin, unit up-normal)`` of the plane the tented case stands on.

    Pitched about X only, so it slopes front-to-back and never side to side: the south edge
    sits at ``-TENT_WEDGE_MIN_H`` and it falls away northward at ``TENT_ANGLE_DEG``. Stand
    that plane on a desk and it goes flat, tipping the whole assembly — plate, PCB, switch
    plate, top case — forward by the tent angle as one rigid body. Nothing inside moves
    relative to anything else, which is the entire point: the Z ladder is untouched."""
    th = math.radians(C.TENT_ANGLE_DEG)
    return (0.0, 0.0, -C.TENT_WEDGE_MIN_H), (0.0, math.sin(th), math.cos(th))


def tent_ground_z(y: float) -> float:
    """Z of the tent plane at a given case-Y — i.e. the underside of the bottom case there."""
    origin, up = tent_plane()
    return origin[2] - (up[1] / up[2]) * (y - origin[1])


def _below_plane_cutter(origin: tuple[float, float, float],
                        up: tuple[float, float, float]) -> Part:
    """Half-space solid filling everything below the given plane."""
    big = 500.0
    box = Solid.make_box(big, big, big).translate((-big / 2, -big / 2, -big))
    return cast(Part, Plane(origin=origin, z_dir=up).location * box)


@cache
def wedge_deep_z() -> float:
    """Z of the wedge's deepest point — its north edge.

    NOT ``-TENT_WEDGE_MAX_H``. That constant is the depth at ``OUTER_DEPTH``, i.e. at the
    TUB's outline; the wedge rides the PLATE's rim profile, which stops SEAM_SKIN +
    SEAM_FIT_CLEAR short of it and so tops out around y=123.8. The constant stays a safe
    upper bound for sizing the stock; this is what the part actually reaches."""
    rim_outer = C.PCB_XY_CLEARANCE + C.SEAM_RIM_THK
    y_max = offset_extruded(rim_outer, 0.0, 1.0).bounding_box().max.Y
    return tent_ground_z(y_max)


def _below_seam_cutter() -> Part:
    """Everything BELOW the top case's bottom edge, as a solid swept across the full width.

    The edge profile is drawn once in the Y-Z plane and extruded along X, so every wall gets
    the same handover with no per-wall special casing — it is a function of Y alone.

    Three stretches, south to north: running parallel to the tent plane; a SPLINE sweeping up
    off it; then flat at ``SEAM_NORTH_RISE_Z``. The spline is given the tent plane's slope as
    its start tangent and horizontal as its end tangent, so it leaves the desk and arrives at
    the northern run tangentially — swept, not kinked.

    The southern run is offset ``TENT_SKIRT_LIFT`` ABOVE the plane rather than lying on it, so
    the skin floats clear of the desk and a band of bottom case shows beneath it. Offsetting
    the whole profile (spline start included) keeps the tangency: the run is still parallel to
    the plane, so the sweep still leaves it without a kink.

    The NORTHERN run used to be Z=0 flat. It now sits at ``SEAM_NORTH_RISE_Z``, which is 0 only
    when that dial is. Everything below the profile is the cutter, so raising the northern run
    carves the tub's skin off the wall up to that height and hands the face to the bottom part.
    That is safe at any height up to ``SEAM_LEDGE_Z`` and no higher: below the ledge the tub is
    ONLY its outer skin — ``_plate_pocket`` has already taken the floor and inner wall out from
    behind it — so the cutter eats skin and nothing else. Above the ledge it would start eating
    the tub proper, which is what ``SEAM_NORTH_RISE_FRAC``'s ceiling of 1.0 exists to prevent.

    Note the steepening: the sweep climbs from the southern run to the northern one over a run
    fixed by ``TENT_SEAM_RAMP_FRAC``, so the higher the dial the steeper that climb — 3.14 mm
    over 8.8 mm at frac 0, 9.44 mm over the same 8.8 mm at frac 1. The joins stay tangent
    either way, but lengthening the ramp is the lever if the blend starts to read as a corner."""
    y1, y2 = C.TENT_SEAM_Y1, C.TENT_SEAM_Y2
    lift = C.TENT_SKIRT_LIFT
    rise = C.SEAM_NORTH_RISE_Z
    z1 = tent_ground_z(y1) + lift
    slope = -math.tan(math.radians(C.TENT_ANGLE_DEG))
    y_s, y_n = -20.0, C.OUTER_DEPTH + 60.0
    z_s = tent_ground_z(y_s) + lift
    bot = wedge_deep_z() - 20.0
    with BuildSketch(Plane.YZ) as sk:            # sketch u -> case Y, sketch v -> case Z
        with BuildLine():
            # The cutter starts 20 mm south of the case, by which point the LIFTED plane has
            # risen above Z=0. Hold the profile at Z=0 until it drops back under: the cutter
            # must never reach above Z=0 anywhere, or it eats the tub proper, not the skirt.
            # (Purely a guard on the overhang — the case itself starts at y=0.)
            if z_s > 0.0:
                Line((y_s, 0.0), (y_s - z_s / slope, 0.0))
                Line((y_s - z_s / slope, 0.0), (y1, z1))
            else:
                Line((y_s, z_s), (y1, z1))
            Spline((y1, z1), (y2, rise), tangents=((1.0, slope), (1.0, 0.0)))
            Line((y2, rise), (y_n, rise))
            Line((y_n, rise), (y_n, bot))
            Line((y_n, bot), (y_s, bot))
            Line((y_s, bot), (y_s, min(0.0, z_s)))   # back to wherever the run actually started
        make_face()
    return _extrude_across_x(sk)


def _extrude_across_x(sk: BuildSketch) -> Part:
    """Take a Y-Z profile sketch and sweep it across the full width of the case.

    Extrudes the LOCATED face functionally, along its own +X normal. Doing it via
    `add(sketch)` inside a BuildPart instead loses the plane association and extrudes along
    global +Z — which yields a zero-thickness solid that silently deletes everything it is
    subtracted from."""
    face = sk.sketch.faces()[0]  # type: ignore[union-attr]
    solid = extrude(face, amount=C.OUTER_WIDTH + 120.0)
    return cast(Part, solid.translate((-60.0, 0.0, 0.0)))


def skirt_extension() -> Part:
    """The TOP case's skin carried on below Z=0, down toward the desk over the southern stretch.

    Only the outer ``SEAM_SKIN`` band — the same ring the tub's wall already is below the
    rabbet ledge — so it descends OUTBOARD of the wedge (which is inset SEAM_SKIN +
    SEAM_FIT_CLEAR) and the two never meet. Bounded above by Z=0 and below by the seam
    profile, which is what makes it die away to nothing by ``TENT_SEAM_Y2``.

    It stops ``TENT_SKIRT_LIFT`` short of the tent plane rather than landing on it, so the
    wedge alone carries the ground contact and a reveal of bottom case shows under the skin.

    Adds no height: it fills space that already existed between Z=0 and the tent plane."""
    outer = C.WALL_THICKNESS + C.PCB_XY_CLEARANCE
    pocket_outer = C.PCB_XY_CLEARANCE + C.SEAM_RIM_THK + C.SEAM_FIT_CLEAR
    z_bot = wedge_deep_z() - 1.0
    band = cast(Part, offset_extruded(outer, z_bot, 0.0, rounded=True)
                - offset_extruded(pocket_outer, z_bot - 1.0, 0.1))
    # Keep only what lies BETWEEN the seam and Z=0. Subtracting everything below the seam does
    # both jobs at once: south of y1 the seam IS the tent plane, so this trims the skin to the
    # desk; north of y2 the seam IS Z=0, so the skin vanishes and the wedge shows instead.
    band = cast(Part, band - _below_seam_cutter())
    return cast(Part, band - _lead_in_relief(z_bot))


def _lead_in_relief(z_bot: float) -> Part:
    """Cutter that widens the channel mouth so the bottom case can find it.

    Where the skin descends past the wedge the two form a channel with only ``SEAM_FIT_CLEAR``
    (0.2 mm) between them, and its mouth is at the SEAM — just above the desk over the southern
    stretch, not at Z=0. ``_chamfer_pocket_mouth``'s Z=0 starter is buried inboard there and
    does nothing, so without this the bottom case has to arrive within 0.2 mm to start.

    BUILT AS A CUTTER, NOT A CHAMFER, and that is deliberate. OCC propagates a chamfer along
    the tangent-continuous edge chain, and this one runs through a 0.84 mm arc at the SE corner
    (the 3.25 mm offset radius turning 14.7°). That arc poisons the whole front-and-east chain
    at ANY leg — it was verified to fail down to 0.05 mm — so chamfering succeeded on the west
    and thumb edges and silently skipped the rest, leaving half the perimeter square. A cutter
    is uniform, exact, and has no propagation or edge-ordering failure mode at all.

    It is a square relief rather than a 45° taper: the inner face steps out by ``SEAM_LEAD_IN``
    for the bottom ``SEAM_LEAD_IN`` of the channel. Measured from the SEAM (this is the seam
    cutter shifted up by that much) rather than from a plane, so it tracks the sweep through
    the blend as well as the flat run.

    The stock's ceiling TRACKS THE MOUTH rather than being a constant. North of the sweep the
    mouth is not near Z=0 any more — it is up at ``SEAM_NORTH_RISE_Z``, wherever the dial puts
    it — and a stock capped just above Z=0 would sit entirely below the thing it is supposed to
    open, leaving the plate rim to find a square 0.2 mm channel unaided over the whole northern
    half.

    It is capped, though, and not simply run to the ledge. Anywhere ABOVE Z=0 this relief eats
    POCKET WALL — the face the plate rim seats against — so it is opened only where the mouth
    genuinely needs it, and then by exactly ``SEAM_LEAD_IN``.

    With the dial at 0 the mouth sits ON Z=0, which is precisely where ``_chamfer_pocket_mouth``
    puts the tub-side starter, so nothing is owed here and the stock stops at 0.1 as it always
    did. Lift the mouth off that plane and the chamfer is stranded below it — then, and only
    then, this has to reach up and open the mouth itself."""
    pocket_outer = C.PCB_XY_CLEARANCE + C.SEAM_RIM_THK + C.SEAM_FIT_CLEAR
    stock_top = (0.1 if C.SEAM_NORTH_RISE_Z <= 0.0
                 else C.SEAM_NORTH_RISE_Z + C.SEAM_LEAD_IN + 0.1)
    wide = offset_extruded(pocket_outer + C.SEAM_LEAD_IN, z_bot - 1.0, stock_top)
    above_mouth = cast(Part, _below_seam_cutter().translate((0.0, 0.0, C.SEAM_LEAD_IN)))
    return cast(Part, wide & above_mouth)


def tent_wedge() -> Part:
    """The bottom case's tent wedge: the block below Z=0 that stands the keyboard at an angle.

    Follows the PLATE's own rim profile, so the bottom case stays inset behind the tub's skin
    by SEAM_SKIN + SEAM_FIT_CLEAR (2.3 mm) — the "skinny" look. The tub's skin therefore ends
    at Z=0 and floats clear of the desk; it is carried by the screws through the standoffs and
    by its rabbet on the plate rim, not by the wedge.

    Being the same profile as ``_plate_envelope`` is what keeps this cheap: no need to chase
    the tub's real footprint (the +Y bump squares the NW corner off proud of the nominal
    offset and carries a fillet), and no tray build inside ``build_bottom_part``.

    ``TENT_WEDGE_MIN_H`` thick at the south, climbing to ``TENT_WEDGE_MAX_H`` at the north.
    Solid rather than shelled — only a few mm thick, and the mass is welcome."""
    rim_outer = C.PCB_XY_CLEARANCE + C.SEAM_RIM_THK
    stock = offset_extruded(rim_outer, -(C.TENT_WEDGE_MAX_H + 1.0), 0.0)
    return cast(Part, stock - _below_plane_cutter(*tent_plane()))


def ground_face(part: Part):
    """The wedge's underside — the face that meets the desk — or None.

    Selected by "parallel to the tent plane AND lying ON it", not by lowest centre. On a
    tilted plane, lowest-centre is simply wrong: a foot seat's floor near the north sits at
    Z ≈ -4.2 while the main ground face's CENTRE is at Z ≈ -3.2, so the seat wins and you
    end up chamfering a foot recess instead of the case's rim."""
    origin, up = tent_plane()
    on_plane = []
    for f in part.faces().filter_by(GeomType.PLANE):
        n = f.normal_at(f.center())
        if abs(n.Z + up[2]) > 0.02 or abs(n.Y + up[1]) > 0.02:
            continue                                  # not parallel to the tent plane
        c = f.center()
        gap = ((c.X - origin[0]) * up[0] + (c.Y - origin[1]) * up[1]
               + (c.Z - origin[2]) * up[2])
        if abs(gap) > 1e-3:
            continue                                  # parallel, but offset from it
        on_plane.append(f)
    return max(on_plane, key=lambda f: f.area) if on_plane else None


def _chamfer_wedge_ground_edge(part: Part) -> Part:
    """Counter-chamfer the wedge's ground rim (elephant-foot pre-compensation).

    The bottom case now meets the desk on the tilted wedge face, not at Z=0, so this is where
    the squished first layers would otherwise bulge past the footprint. Falls back to a
    smaller leg, then to none, rather than aborting the build."""
    ground = ground_face(part)
    if ground is None:
        return part
    for length in (C.BOTTOM_CHAMFER, C.BOTTOM_CHAMFER * 0.5):
        try:
            return cast(Part, chamfer(ground.outer_wire().edges(), length=length))
        except (ValueError, Standard_Failure):
            continue
    return part


def _foot_recesses() -> Part:
    """Cutter: shallow Ø FOOT_DIA seats in the OUTER bottom face (Z=0) at FOOT_POSITIONS.

    Stick-on rubber feet locate in these seats at the 4 corners so the keyboard grips
    the desk. Each cylinder starts 0.5 mm outside the face (so it opens cleanly, no
    coincident face) and recesses FOOT_DEPTH into the material.

    Cut PERPENDICULAR to the tent plane, not plumb. The ground face is tilted now, so a
    vertical cylinder would meet it obliquely — the seat depth would vary by ±0.17 mm across
    a Ø10 seat and the pad would sit on a slight ramp instead of flat against the desk.
    """
    _origin, up = tent_plane()
    seats = None
    for x, y in C.FOOT_POSITIONS:
        z = tent_ground_z(y)
        start = (x - up[0] * 0.5, y - up[1] * 0.5, z - up[2] * 0.5)
        cyl = Solid.make_cylinder(C.FOOT_DIA / 2, C.FOOT_DEPTH + 0.5,
                                  Plane(origin=start, z_dir=up))
        seats = cyl if seats is None else cast(Part, seats + cyl)
    assert seats is not None
    return cast(Part, seats)


def build_bottom_part(side: Side) -> Part:
    """BOTTOM clamshell part: the inset floor plate + full standoffs.

    A thin plate (``_plate_envelope``: floor to ``SEAM_LEDGE_Z``, inset behind the
    tub skin) that tucks up into the tub's rabbet pocket. The standoffs are added on
    top so they keep their full height and rise to their tap tops (``PLATE_SEAT_Z``);
    the TOP tub clamps down onto them via the existing top-down join screws. The
    battery pocket is recessed into the plate floor. The plate bottom is flush at
    ``Z = 0`` (sole ground contact goes to the user's stick-on rubber pads)."""
    if side not in ("left", "right"):
        raise ValueError(f"side must be 'left' or 'right', got {side!r}")

    bottom = _plate_envelope()
    # The tent wedge IS the bottom case below Z=0: same rim profile as the plate, so it stays
    # inset behind the tub's skin, thin at the south and thick at the north. Added, never cut —
    # see the tent section in constants.py for why cutting would wreck the Z ladder.
    bottom = cast(Part, bottom + tent_wedge())
    for hx, hy in C.MOUNTING_HOLES:
        cx, cy = C.pcb_to_case(hx, hy)
        bottom = cast(Part, bottom + stepped_standoff(at=(cx, cy)))

    bottom = cast(Part, bottom - battery_pocket())
    bottom = cast(Part, bottom - _foot_recesses())
    bottom = _chamfer_wedge_ground_edge(_as_part(bottom))
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

    # Round the vertical corners into arcs (rounded-rectangle plan) — the OUTER wall's
    # four corners ONLY.
    #
    # Selecting by edge length alone did not do that, and the plateau bottomed out on the
    # encoder because of it. The CAVITY's four vertical corners are cav_z1 − cav_z0 = 4.2 mm
    # tall, comfortably past the 2.0 mm cut-off, so they were filleted too — and rounding a
    # concave corner puts material back INTO the cavity. An R3.0 arc on the 13.5 mm square
    # cavity reaches only 8.32 mm diagonally from the encoder centre, while the EC11's
    # 12.4 mm square body has its corners at 8.77: a 0.45 mm bite out of each of the four
    # corners of the box this plateau exists to clear, over the box's whole proud height
    # (Z 15.0 → 17.0). Measured 2.03 mm³ of interference on the built TOP. The plateau
    # landed on the encoder and held the entire TOP part off the switch plate — with the
    # keyboard installed the shell would seat at the north OR the south and rock about
    # the encoder, while the empty shells mated perfectly.
    #
    # Filter radially, not by length: cavity corners sit at Chebyshev radius cav_w/2 from
    # the encoder centre, outer corners at outer_w/2, so the midpoint separates them and
    # tracks any future wall thickness.
    corner_r_min = (cav_w / 2 + outer_w / 2) / 2
    vert = [e for e in shell.edges()
            if abs(e.tangent_at(0.5).Z) > 0.9 and e.length > 2.0
            and max(abs(e.center().X - enc_cx),
                    abs(e.center().Y - enc_cy)) > corner_r_min]
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
    AFTER the canopy is fused, lowering both the wall and the cover in one op. It is a TOP-only
    feature (the BOTTOM is a separate inset plate below the rabbet ledge — untouched; access is
    from the top/side, not from below). See the slide-switch section in ``constants.py``.

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
    """TOP clamshell part: the deep tub (full outer skin) + switch membrane.

    The full-height tray (outer wall to the ground) has the inset plate pocket
    carved from its base, then the plate-shaped membrane (from ``top_cover``) is
    fused on as the ceiling. The membrane already carries its switch windows, open
    MCU/OLED/JST bay and M2 clearance holes; it is grown by ``COVER_FUSE_MARGIN`` so
    it bites into the upper walls and the whole TOP is one solid. Standoffs are NOT
    part of the TOP — they live in the BOTTOM plate and pass up through the open cavity.

    The bay canopy is FUSED on here (``build_canopy``): its ramp grows out of the cover
    surface and merges into it (its base overlaps the cover for a clean union), so the MCU
    hood is integral to the TOP — not a separate part.

    **The TOP is the one part that is NOT mirror-identical between halves.** The two builds
    carry the nice!nano in opposite orientations (``C.MCU_ORIENTATION``: left flipped, right
    neutral), so the canopy's USB port sits at a different Z on each — left 16.84→21.5, right
    19.6→24.26. Everything else, ridge included, is common, so the silhouette (and the bounding
    box) still matches; only the window band moves. ``build_bottom_part`` and the legacy
    ``build_case_half`` remain strict mirrors.

    Finally two −X cuts carve the slide switch: the wide finger ``_slide_scoop`` (tray look)
    and then the ``_slide_actuator_cavity`` (a switch-shaped drop-in pocket). Both are TOP
    features; the BOTTOM plate is a separate body below the rabbet ledge, untouched."""
    if side not in ("left", "right"):
        raise ValueError(f"side must be 'left' or 'right', got {side!r}")

    # Deep tub: the FULL-height tray (outer skin to the ground), then carve the inset
    # plate pocket out of its base. This leaves the SEAM_SKIN skirt as the descending
    # outer wall — no mid-wall seam — and the rabbet ledge that receives the plate rim.
    top = cast(Part, build_tray(rim_z=C.COVER_TOP_Z, bottom_chamfer=False) - _plate_pocket())
    top = _chamfer_pocket_mouth(top)   # tub-side starter chamfer at the pocket mouth
    # Carry the skin down to the desk over the southern stretch, so the front of the case
    # reads as one piece and the bottom wedge only shows further north. Costs no height.
    top = cast(Part, top + skirt_extension())
    # ...and north of the sweep, carve the skin back UP the wall to SEAM_NORTH_RISE_Z, handing
    # that band of face to the bottom part. The skirt only ever trimmed its own band, all of it
    # below Z=0; the raised northern run cuts into the tub itself, so the same profile has to
    # come off the whole part and not just the band. Everything fused on after this sits at
    # COVER_TOP_Z or above, well clear of the cut.
    top = cast(Part, top - _below_seam_cutter())
    # The mouth of the rabbet pocket rides up with the parting line, so its lead-in has to come
    # off the tub itself here — north of the sweep there is no skirt band left for
    # skirt_extension to have taken it out of.
    #
    # Gated, because this one is not a no-op when the dial is off: skirt_extension only ever
    # subtracts the relief from its own band, all of it below Z=0, and taking it off the whole
    # tub would additionally shave the 0.1 mm of pocket wall the stock reaches above Z=0. Small
    # (~7 mm³) and harmless, but it would mean frac 0 no longer reproduces the un-dialled case.
    if C.SEAM_NORTH_RISE_Z > 0.0:
        top = cast(Part, top - _lead_in_relief(wedge_deep_z() - 1.0))
    top = cast(Part, top + build_top_cover(fuse_margin=C.COVER_FUSE_MARGIN))
    top = cast(Part, top + _encoder_shell())
    top = cast(Part, top + build_canopy(side=side))
    # USB port re-cut AFTER the fuse: the flipped half's port floor sits below COVER_TOP_Z, so
    # the cover backfills the bottom of the window otherwise. See canopy.usb_port_cutter.
    top = cast(Part, top - usb_port_cutter(side))
    # Slide-switch finger scoop: cut AFTER the canopy fuse so it lowers the wall + cover together.
    top = cast(Part, top - _slide_scoop())
    # Slide-switch drop-in pocket: registered switch-shaped cavity.
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
        # side-matched: the jack stub's Z band follows this half's MCU orientation
        parts.append(_mirror_part(build_pcb_phantom(_SIDE)))
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
