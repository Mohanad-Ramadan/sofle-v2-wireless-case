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
from build123d import (Part, Face, mirror, Plane, Pos, Rot, fillet, chamfer, Axis, BuildPart,
                       BuildSketch, BuildLine, Line, Spline, Locations, Cylinder,
                       Sphere, Solid, Box, Location, GeomType, add, extrude, make_face,
                       RectangleRounded, Rectangle, Polyline, revolve, loft, Circle)
from OCP.Standard import Standard_Failure
from OCP.ShapeFix import ShapeFix_Shape
from OCP.TopoDS import TopoDS
from . import constants as C
from .pcb_geometry import slide_switch_placement, rotate_2d
from .tray import build_tray, offset_extruded
from .standoffs import stepped_standoff
from .battery import battery_pocket, jst_pocket, jst_wire_channel
from .top_cover import build_top_cover, _load_plate_cutouts
from .canopy import build_canopy, usb_port_cutter, CANOPY_RIDGE_TOP_Z
# snaps imports wedge_deep_z/tent_ground_z from here, but only inside its functions, so this
# top-level import does not close a cycle.
from .snaps import snap_reliefs, snap_barbs, snap_catches, snap_gap_footprints
from . import canopy_puzzle as PZ


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
    shell -= jst_pocket()
    shell -= jst_wire_channel()

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
    upper bound for sizing the stock; this is what the wedge actually reaches.

    THE WEDGE, not the bottom part. Those parted company when the visible band started standing
    proud of the skin — see ``bottom_deep_z``."""
    rim_outer = C.PCB_XY_CLEARANCE + C.SEAM_RIM_THK
    y_max = offset_extruded(rim_outer, 0.0, 1.0).bounding_box().max.Y
    return tent_ground_z(y_max)


def bottom_deep_z() -> float:
    """Z of the BOTTOM PART's deepest point — which is not the wedge's.

    The wedge stops at the plate rim, ~2.2 mm inside the tub's skin, so it bottoms out at
    y≈123.8. The visible band is flush with the skin, so it runs the full ``OUTER_DEPTH`` to
    y=126 — and the desk is still falling over those last 2.2 mm.

    ASKED OF THE OUTLINE, not of a constant. ``tub_outline_face()`` is the same silhouette the
    band is extruded from, so this cannot drift from what the band actually reaches.

    It was 0.158 mm deeper while the band flared 1.5 mm proud: the footprint ran out to y≈127.5
    then, and that overhang was the only height the flare cost.

    THE WHOLE UNDERSIDE DROPPED ``_skin_drop()`` for the blind-port skin: the skin rides the
    wedge's rim profile and the visible band is re-trimmed to the same skin desk, so BOTH fall by
    the drop. The band still reaches furthest north (the tub outline, past the wedge), so it is
    still the deepest point — just a drop lower than before."""
    band_deep = tent_ground_z(tub_outline_face().bounding_box().max.Y)
    return min(band_deep, wedge_deep_z()) - _skin_drop()


def _seam_sweep_params():
    """The ramp's knots and its end tangents — one definition, three consumers.

    ``_below_seam_cutter`` draws the spline and ``seam_profile_min_z`` / ``seam_profile_max_z``
    measure it, and they must all be measuring the SAME curve. Kept here rather than duplicated
    so they cannot drift apart when a dial moves.

    Returns the full knot list, south end first, INCLUDING both endpoints. It used to return
    exactly two points and be typed that way by its callers; the wave needs interior knots (see
    ``SEAM_WAVE_KNOTS``), and a through-fit spline over 2 points is precisely the old curve, so
    this generalises rather than replaces. The tangents are unchanged and still do the same job:
    the tent plane's own slope at the south so the ramp leaves the run without a kink, and
    horizontal at the north so it arrives on the flat run the same way.

    THE KNOTS ARE CONVERTED HERE, not read off ``SEAM_WAVE_Y``. That constant holds the same
    arithmetic, but frozen at the angle the module was imported at; this reads the tent plane
    live, so monkeypatching ``TENT_ANGLE_DEG`` moves the wave with the desk instead of leaving
    it behind. The constant exists for the import-time guards, which have no plane to ask."""
    y1, y2 = C.TENT_SEAM_Y1, C.TENT_SEAM_Y2
    # ONLY the southern run drops with the desk. Over the south the parting line floats
    # TENT_SKIRT_LIFT above the DESK, and the desk is the blind-port skin now (skin_ground_z, a
    # _skin_drop() below the wedge), so z1 rides that — which is what keeps the top skin covering
    # to the new desk and the front reveal at TENT_SKIRT_LIFT instead of opening by the skin drop.
    # The WAVE keeps its designed shape on the wedge ground: its reveal is measured DOWN from the
    # parting line (SEAM_REVEAL_H), not up from the desk, so it need not move — and moving it would
    # reshape the lens (the tail blends between a dropped south and the fixed SEAM_NORTH_RISE_Z
    # north, so it goes shallower). The band's own bottom reaches the new desk via the skin-ground
    # trim in _bottom_outer_shell. So the ramp simply climbs from a _skin_drop()-lower z1 to the
    # unchanged wave. See .omc/specs/deep-dive-bottom-cover-inlay.md.
    z1 = skin_ground_z(y1) + C.TENT_SKIRT_LIFT
    slope = -math.tan(math.radians(C.TENT_ANGLE_DEG))
    # The bottom case's full height at the back — the yardstick the band fractions are in.
    # tent_ground_z(OUTER_DEPTH) IS -TENT_WEDGE_MAX_H, asked of the live plane.
    wedge_max_h = -tent_ground_z(C.OUTER_DEPTH)
    wave = tuple((u * C.OUTER_DEPTH,
                  band * wedge_max_h + tent_ground_z(u * C.OUTER_DEPTH))
                 for u, band in C.SEAM_WAVE_KNOTS)
    knots = ((y1, z1), *wave, (y2, C.SEAM_NORTH_RISE_Z))
    # THE END TANGENT IS NOT HORIZONTAL, and that is the whole reason the ramp reaches the back
    # edge now. A horizontal arrival flattens the line while the desk keeps dropping away beneath
    # it, so the visible band starts WIDENING again over the last stretch — the profile turned
    # back up at the end. It has to keep descending, and faster than the desk does, or the band
    # cannot still be closing when the case runs out. SEAM_TAIL_SLOPE is that rate, and it is
    # stated as a multiple of the desk's own slope so it stays correct at any tent angle.
    tail = slope * C.SEAM_TAIL_SLOPE
    return knots, ((1.0, slope), (1.0, tail))


def _seam_ramp_edge():
    """The ramp as a single OCC edge — built once, measured by everything that needs a number."""
    knots, tangents = _seam_sweep_params()
    with BuildLine() as bl:
        Spline(*knots, tangents=tangents)
    return bl.line.edges()[0]


def seam_profile_min_z() -> float:
    """The LOWEST Z the parting line actually reaches — which is NOT the southern run's end.

    The southern run descends northward (it is parallel to the tent plane), so its lowest point
    is its northern end at ``TENT_SEAM_Y1``. The sweep then leaves that point along the plane's
    own slope, because tangency is the whole design intent — a horizontal departure would put a
    visible kink in the parting line. Leaving tangentially means the spline keeps DESCENDING
    for a few mm before it curves up, so the profile's true minimum sits a little south of the
    ramp's midpoint and a little BELOW z1:

        angle    dip below z1     where
         3 deg      0.024 mm      y = 63.9
         7 deg      0.074 mm      y = 64.2
        10 deg      0.123 mm      y = 64.3

    THE DIP COSTS NO GROUND CLEARANCE, and that is the point worth keeping. It is measured
    against z1, a single number; the DESK is a tilted plane that keeps dropping northward and
    drops faster than the spline does. Perpendicular to the desk the skin's closest approach is
    0.4963 mm at 7 deg, i.e. essentially the full ``TENT_SKIRT_LIFT`` — the dip never eats into
    it. ``test_the_skin_never_touches_the_desk`` measures that invariant directly and is the one
    to trust for clearance.

    It exists so tests can state the tub's floor EXACTLY instead of asserting z1 with enough
    slack to hide the difference. At 3 deg the dip was 0.024 and every such assertion carried a
    0.05 tolerance, so it fitted underneath and nobody had to know; at 7 deg it is 0.074 and
    four assertions failed at once. They were never quite right — the angle only made it
    visible."""
    edge = _seam_ramp_edge()
    # Sketch-local (u, v) here maps to (case Y, case Z), so .Y on the sampled point is the Z.
    lo = min((edge @ (i / 400.0)).Y for i in range(401))
    return min(lo, _seam_sweep_params()[0][0][1])


def seam_profile_max_z() -> float:
    """The HIGHEST Z the parting line reaches anywhere over the case, measured off the curve.

    Companion to ``seam_profile_min_z``, and it exists for the same reason: so callers ask the
    INSTALLED profile what it does instead of reading a dial and assuming.

    ``_lead_in_relief`` is the caller that needed it. Both its stock ceiling and the gate in
    ``build_top_part`` used to test ``SEAM_NORTH_RISE_Z > 0.0`` — a constant, not a property of
    the curve. That is only the same question while the northern run is the profile's high
    point. Any profile that climbs above Z=0 some other way (a crest mid-depth, say) would ship
    with the channel mouth unopened and NOTHING WOULD FAIL, because the thing being asked is not
    the thing that matters. Same defect class as the sweep dip: a test written against a dial
    rather than against the geometry.

    Bounded to the case's own footprint. South of y=0 the cutter deliberately rides up to Z=0 as
    an overhang guard (see ``_below_seam_cutter``), and that stretch is not parting line — it is
    outside the part and must not drag the answer up with it."""
    edge = _seam_ramp_edge()
    hi = max((edge @ (i / 400.0)).Y for i in range(401))
    # The southern run is parallel to the tent plane, which rises going south, so its high point
    # inside the case is at y=0. North of the ramp the run is flat at SEAM_NORTH_RISE_Z. The south
    # run rides the SKIN ground now (see _seam_sweep_params), so its y=0 high point is measured
    # there too.
    return max(hi, C.SEAM_NORTH_RISE_Z, skin_ground_z(0.0) + C.TENT_SKIRT_LIFT)


def _below_seam_cutter() -> Part:
    """Everything BELOW the top case's bottom edge, as a solid swept across the full width.

    The edge profile is drawn once in the Y-Z plane and extruded along X, so every wall gets
    the same handover with no per-wall special casing — it is a function of Y alone.

    Three stretches, south to north: running parallel to the tent plane; a SPLINE ramp; then flat
    at ``SEAM_NORTH_RISE_Z``. The spline is given the tent plane's slope as its start tangent and
    horizontal as its end tangent, so it leaves the desk and arrives at the northern run
    tangentially — swept, not kinked.

    The ramp is a THROUGH-FIT over ``SEAM_WAVE_KNOTS``, not a two-point hump, and that is what
    makes the bottom case read as a lens instead of a skirt: it crests above Z=0 around u=0.67
    and eases back down. A two-point spline between the runs is monotonic by construction, so
    the visible band could only widen northward. See the knot table for where the shape came
    from and how far to trust it.

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
    knots, sweep_tangents = _seam_sweep_params()
    (y1, z1), (y2, rise) = knots[0], knots[-1]
    lift = C.TENT_SKIRT_LIFT
    slope = -math.tan(math.radians(C.TENT_ANGLE_DEG))
    y_s, y_n = -20.0, C.OUTER_DEPTH + 60.0
    z_s = skin_ground_z(y_s) + lift   # south run rides the skin desk, parallel to the plane
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
            Spline(*knots, tangents=sweep_tangents)
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


@cache
def seam_skirt_tub() -> Part:
    """The deep tub exactly as ``skirt_extension`` must see it: plate pocket carved, mouth NOT
    yet chamfered. One definition so ``build_top_part`` and the tests cannot disagree about
    which of the two states the skirt is sectioned from — see ``skirt_extension``.

    CACHED because the bottom part needs it too now (``tub_outline_face``), and it builds a
    whole tray. ``build_bottom_part`` never touched a tray before this; without the cache the
    suite pays for one per bottom build."""
    return cast(Part, build_tray(rim_z=C.COVER_TOP_Z, bottom_chamfer=False) - _plate_pocket())


@cache
def tub_outline_face() -> Face:
    """The TOP case's real outer outline at Z=0, filled — the silhouette the bottom must match.

    Sectioned rather than reconstructed, for the same reason ``skirt_extension`` sections: the
    outline is not a polygon offset. It carries the +Y relief bump (``_bump_facet_south_y``,
    y=115) squared off proud of the nominal offset, and that bump's NW corner fillet. Offsetting
    the PCB polygon instead is what put the bottom case 36 mm outside the top at y=115 when the
    two were compared from below.

    OUTER WIRE ONLY. At Z=0 the tub is a ring — ``_plate_pocket`` has taken the floor and inner
    wall out from behind the skin — so the section comes back with an inner wire too, which is
    the pocket bore and is not this outline. Filling from the outer wire alone gives the plan
    silhouette rather than the wall's cross-section.

    Taken at Z=0 exactly, below the mouth chamfer, and from the UN-chamfered tub, for the
    reasons ``skirt_extension`` spells out."""
    tub = seam_skirt_tub()
    slab = cast(Part, tub & Solid.make_box(400.0, C.OUTER_DEPTH + 200.0, 0.05)
                .translate((-100.0, -100.0, 0.0)))
    section = slab.faces().filter_by(Plane.XY).sort_by(Axis.Z)[0]
    return cast(Face, make_face(section.outer_wire()))


def skirt_extension(tub: Part) -> Part:
    """The TOP case's skin carried on below Z=0, down toward the desk.

    Only the outer ``SEAM_SKIN`` band — the same ring the tub's wall already is below the
    rabbet ledge — so it descends OUTBOARD of the wedge (which is inset SEAM_SKIN +
    SEAM_FIT_CLEAR) and the two never meet. Bounded above by Z=0 and below by the seam profile,
    which is what makes it appear and die away on its own wherever that profile crosses Z=0.

    It stops ``TENT_SKIRT_LIFT`` short of the tent plane rather than landing on it, so the
    wedge alone carries the ground contact and a reveal of bottom case shows under the skin.

    Adds no height: it fills space that already existed between Z=0 and the tent plane.

    THE OUTLINE IS THE TUB'S OWN CROSS-SECTION, taken at Z=0 and projected straight down —
    not a polygon offset. That is what lets the skirt run the WHOLE perimeter, including the
    rear, and it is the difference between this and the version that could only work south of
    the +Y relief bump. The bump stands proud of the nominal offset and carries a corner
    fillet, so a polygon-offset band reaching it would sit INSIDE the wall above and leave a
    step at Z=0 all along the bump's face; ``TENT_SEAM_FRAC_MAX`` existed to keep the skirt
    away from that region rather than solve it. Sectioning the tub solves it for every wall
    feature at once, present and future, because the band is by construction whatever the wall
    directly above it is.

    PASS THE UN-CHAMFERED TUB. The section is taken at Z=0, and that is precisely where
    ``_chamfer_pocket_mouth`` sits: a 45° chamfer on the mouth edge takes material from the bore
    AND from the Z=0 face, so a chamfered tub hands back a bore already set back
    ``SEAM_POCKET_LEAD_IN``. The band inherits it, the channel's own ``SEAM_LEAD_IN`` relief
    then has 0.4 mm less to cut, and the mouth measures 0.2 mm of lead-in instead of 0.6 — the
    two starters cancelling instead of stacking. The mouth chamfer belongs to the pocket, not to
    the wall, and must not run down the skirt."""
    z_bot = wedge_deep_z() - 1.0
    slab = cast(Part, tub & Solid.make_box(400.0, C.OUTER_DEPTH + 200.0, 0.05)
                .translate((-100.0, -100.0, 0.0)))
    face = slab.faces().filter_by(Plane.XY).sort_by(Axis.Z)[0]
    # DIRECTION GIVEN EXPLICITLY. This face is the slab's underside, so its own normal already
    # points at -Z; `amount=z_bot` (negative) reverses that and builds the band UPWARD through
    # the tub instead — it came back spanning Z 0..15.01 rather than -15.24..0. Same trap as
    # _extrude_across_x's, and the same fix: never leave the direction to the face's normal.
    band = cast(Part, extrude(face, amount=abs(z_bot), dir=(0.0, 0.0, -1.0)))
    # Keep only what lies BETWEEN the seam and Z=0. Subtracting everything below the seam does
    # both jobs at once: where the seam runs below Z=0 this trims the skin to it, and where the
    # seam has climbed above Z=0 the band vanishes entirely and the wedge shows instead.
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

    With the mouth ON Z=0 — which is precisely where ``_chamfer_pocket_mouth`` puts the tub-side
    starter — nothing is owed here and the stock stops at 0.1 as it always did. Lift the mouth
    off that plane and the chamfer is stranded below it; then, and only then, this has to reach
    up and open the mouth itself.

    THE CEILING IS READ OFF THE CURVE, not off ``SEAM_NORTH_RISE_Z``. Those agree only while the
    northern run is the profile's high point; ``seam_profile_max_z`` asks the installed profile
    directly, so a crest anywhere along the depth is served too."""
    pocket_outer = C.PCB_XY_CLEARANCE + C.SEAM_RIM_THK + C.SEAM_FIT_CLEAR
    mouth_z = seam_profile_max_z()
    stock_top = 0.1 if mouth_z <= 0.0 else mouth_z + C.SEAM_LEAD_IN + 0.1
    wide = offset_extruded(pocket_outer + C.SEAM_LEAD_IN, z_bot - 1.0, stock_top)
    above_mouth = cast(Part, _below_seam_cutter().translate((0.0, 0.0, C.SEAM_LEAD_IN)))
    return cast(Part, wide & above_mouth)


def tent_wedge() -> Part:
    """The bottom case's tent wedge: the block below Z=0 that stands the keyboard at an angle.

    Follows the PLATE's own rim profile, so the wedge stays inset behind the tub's skin by
    SEAM_SKIN + SEAM_FIT_CLEAR (2.2 mm). Concentric offsets of one polygon, which is what
    guarantees that clearance everywhere.

    KEEP IT ON THE POLYGON. Putting the wedge on the tub's outline instead — inset 2.2 from it,
    to make the two silhouettes agree in plan — was tried and reverted: an INWARD offset raises
    arcs at the concave corners that bulge toward the wall, so the 0.2 mm fit clearance is not
    preserved there and the two parts overlapped by 197 mm³. Concentric offsets of the same
    polygon cannot do that to each other.

    It costs nothing to stay here. The wedge is only visible south of where the reveal opens,
    and the tub's outline departs from the polygon at the +Y relief bump (y≥115) — nowhere near.
    North of the reveal it is the flared band, not the wedge, that shows, and THAT is on the
    tub's outline (see ``_bottom_outer_shell``).

    ``TENT_WEDGE_MIN_H`` thick at the south, climbing to ``TENT_WEDGE_MAX_H`` at the north.
    Solid rather than shelled — only a few mm thick, and the mass is welcome."""
    rim_outer = C.PCB_XY_CLEARANCE + C.SEAM_RIM_THK
    stock = offset_extruded(rim_outer, -(C.TENT_WEDGE_MAX_H + 1.0), 0.0)
    return cast(Part, stock - _below_plane_cutter(*tent_plane()))


def _skin_drop() -> float:
    """How far the blind-port skin's outer face sits below the wedge ground: gap + skin."""
    return C.BSKIN_GAP + C.BSKIN_THICK


def _skin_ground_plane() -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """The tent plane shifted straight down by ``_skin_drop()`` — the skin's outer (desk) face."""
    origin, up = tent_plane()
    return (origin[0], origin[1], origin[2] - _skin_drop()), up


def skin_ground_z(y: float) -> float:
    """Z of the blind-port skin's outer (desk) face at a given case-Y — the underside now.

    The wedge ground (``tent_ground_z``) dropped a ``_skin_drop()`` when the skin closed the
    ports; this is where the desk, the feet, and the ground chamfer now live."""
    return tent_ground_z(y) - _skin_drop()


def bottom_skin() -> Part:
    """Solid skin closing the underside, grown a ``_skin_drop()`` below the wedge ground.

    Same rim profile as the wedge (``rim_outer``), so it stays inset behind the tub's skin and
    the reveal is untouched. It is the slab between the OLD wedge ground (top) and the new skin
    ground (bottom); ``snap_bottom_gap`` then carves the air pocket under each arm so the skin
    never touches a flexing latch. Added AFTER the reliefs/barbs so it caps the ports from below.
    See .omc/specs/deep-dive-bottom-cover-inlay.md."""
    rim_outer = C.PCB_XY_CLEARANCE + C.SEAM_RIM_THK
    stock = offset_extruded(rim_outer, -(C.TENT_WEDGE_MAX_H + _skin_drop() + 1.0), 0.0)
    above_skin = cast(Part, stock - _below_plane_cutter(*_skin_ground_plane()))
    return cast(Part, above_skin & _below_plane_cutter(*tent_plane()))


def snap_bottom_gap() -> Part:
    """Cutter: the air gap under every arm, between the wedge ground and the skin top.

    Each arm's tall freed-strip footprint (``snap_gap_footprints``), trimmed to the slab between
    the wedge ground (P0) and the skin top (P0 − BSKIN_GAP). Subtracting it from the skin leaves
    BSKIN_GAP of air under each arm and BSKIN_THICK of skin below that — floor-to-rim, never
    arm-to-rim. Entirely below P0, so it removes only skin: the arms and wedge are untouched."""
    origin, up = tent_plane()
    skin_top = (origin[0], origin[1], origin[2] - C.BSKIN_GAP), up
    prisms = snap_gap_footprints()
    above_skin_top = cast(Part, prisms - _below_plane_cutter(*skin_top))
    return cast(Part, above_skin_top & _below_plane_cutter(origin, up))


def _bottom_outer_shell() -> Part:
    """The band of bottom case that SHOWS: the TOP's own outline, carried down to the desk.

    This is the part of the design the old bottom simply did not have. The plate and the wedge
    are both plain offsets inset behind the tub's skin, so every millimetre of bottom case on
    show was the floor of a 2.2 mm recess. Here the visible band is FLUSH — it rides
    ``tub_outline_face()``, the top's own sectioned silhouette, so the two shells share one
    lateral surface exactly and read as a single body split along the wave.

    ONE PRISM, TWO CUTS, and that is the whole point. The outer surface is a plain vertical
    extrusion of the top's outline: 27 lateral faces (planes and cylinders, one per outline
    edge), a ground plane, and a SINGLE face carrying the entire swoosh. No offset, no loft, no
    freeform patch anywhere — which is why it cannot ripple. It is the same construction
    ``skirt_extension`` uses for the top's skirt, which is what makes the two agree.

    It used to flare 1.5 mm proud, keyed to depth below its own (wave-following) top edge. That
    makes the offset a function of both Y and Z, a concentric offset can only vary with Z, and
    so the band had to be stacked out of ~36 Y-slabs — 304 faces and ~7 visible divisions down
    the east wall. See the flush block in constants.py for the four attempts at lofting it as
    one surface and why none of them survived OCC.

    Two cuts define it, plus the inner offset that keeps it a band rather than a slab:
      * everything above ``seam − SEAM_REVEAL_H`` is removed, which is what opens the reveal.
        The cutter is the seam cutter itself, shifted down — the two edges are the same curve,
        so the gap is exactly parallel to the parting line the whole way round;
      * the tent plane trims the bottom, so it lands on the desk with the wedge.

    Where the visible band is shallower than the reveal — the front of the case — the first cut
    takes all of it and nothing is added. That is the bottom case tapering out on its own, and
    it is why the reveal reads as a lens without a lens ever being drawn."""
    rim_outer = C.PCB_XY_CLEARANCE + C.SEAM_RIM_THK
    face = tub_outline_face()
    z_bot = bottom_deep_z() - 1.0
    z_top = C.SEAM_LEDGE_Z
    # THE STOCK STARTS AT THE LEDGE, NOT AT Z=0, and that is not tidiness. tub_outline_face() is
    # a face AT Z=0, so extruding it only downward caps the band there — but the parting line
    # crests at seam_profile_max_z() = 3.87, so the band has to reach 1.87. Capped at zero it
    # loses that 1.87 mm over the crest and the reveal silently opens to 3.87 mm there instead of
    # SEAM_REVEAL_H. Nothing else in the suite sees it; only the crest measurement does.
    #
    # DIRECTION GIVEN EXPLICITLY — the face's own normal already points at -Z, so a negative
    # `amount` builds upward instead. Same trap skirt_extension documents.
    stock = cast(Part, extrude(cast(Part, Pos(0, 0, z_top) * face),
                               amount=z_top - z_bot, dir=(0.0, 0.0, -1.0)))
    band = cast(Part, stock - offset_extruded(rim_outer, z_bot - 1.0, z_top + 1.0))
    # Open the reveal: drop the parting-line cutter by SEAM_REVEAL_H and keep only what is under
    # it. Intersecting (not subtracting) because this cutter IS "everything below the line".
    band = cast(Part, band & _below_seam_cutter().translate((0.0, 0.0, -C.SEAM_REVEAL_H)))
    # Trimmed to the desk LAST, and once, so the underside comes out as a single planar face.
    # The desk is the blind-port SKIN ground now, a _skin_drop() below the wedge, so the visible
    # band reaches down to it instead of stopping short at the old wedge line — otherwise the band
    # would float _skin_drop() proud of the desk with the inset skin poking out beneath it.
    return cast(Part, band - _below_plane_cutter(*_skin_ground_plane()))


@cache
def _seam_ramp_table(_angle: float, _rise: float, _y1: float, _y2: float,
                     n: int = 4001) -> tuple[float, ...]:
    """The ramp resampled onto an even Y grid, built once.

    KEYED ON THE DIALS IT DEPENDS ON. The four arguments are unused inside; they are there so a
    test monkeypatching the tent angle or the north rise gets a fresh table rather than a stale
    one, which is the whole hazard of caching something derived from mutable constants.

    IT EXISTS BECAUSE THE LOOKUP WAS THE BUILD. ``_seam_z_at`` used to rebuild the ramp spline
    and sample it a thousand times on EVERY call — about 12 ms each, and the band's layout asks
    for it a few thousand times. Profiled: one offset 0.00 s, 240 wire samples 0.02 s, a spline
    through 241 points 0.00 s, and 240 of these 2.96 s. That single helper was essentially the
    entire 28 s cost of building the bottom part."""
    edge = _seam_ramp_edge()
    pts = sorted((p.X, p.Y) for p in (edge @ (i / 4000.0) for i in range(4001)))
    out, j = [], 0
    for i in range(n):
        y = C.OUTER_DEPTH * i / (n - 1)
        while j + 2 < len(pts) and pts[j + 1][0] < y:
            j += 1
        (ya, za), (yb, zb) = pts[j], pts[j + 1]
        t = 0.0 if yb == ya else (y - ya) / (yb - ya)
        out.append(za + (zb - za) * t)
    return tuple(out)


def _seam_z_at(y: float) -> float:
    """The parting line's Z at a given case-Y — the three stretches, as the cutter draws them."""
    if y <= C.TENT_SEAM_Y1:
        return skin_ground_z(y) + C.TENT_SKIRT_LIFT   # south run floats above the skin desk
    if y >= C.TENT_SEAM_Y2:
        return C.SEAM_NORTH_RISE_Z
    tbl = _seam_ramp_table(C.TENT_ANGLE_DEG, C.SEAM_NORTH_RISE_Z,
                           C.TENT_SEAM_Y1, C.TENT_SEAM_Y2)
    f = y / C.OUTER_DEPTH * (len(tbl) - 1)
    i = min(int(f), len(tbl) - 2)
    return tbl[i] + (tbl[i + 1] - tbl[i]) * (f - i)


def _shell_y_range() -> tuple[float, float]:
    """Where the visible band exists: from the first Y at which it is taller than the reveal,
    to the back edge. The southern end is the lens's own point — nothing is drawn to make it."""
    ys = [i * C.OUTER_DEPTH / 2000.0 for i in range(2001)]
    for y in ys:
        if _seam_z_at(y) - C.SEAM_REVEAL_H > skin_ground_z(y):   # desk is the skin ground now
            return y, C.OUTER_DEPTH
    raise ValueError("the reveal never opens — SEAM_REVEAL_H is deeper than the band ever gets")


def ground_face(part: Part):
    """The underside face that meets the desk — the wedge's, or the blind-port skin's — or None.

    Selected by "faces DOWN, parallel to the tent plane, and lies on the LOWEST such plane", not
    by lowest centre. On a tilted plane, lowest-centre is simply wrong: a foot seat's floor near
    the north sits at Z ≈ -4.2 while the main ground face's CENTRE is at Z ≈ -3.2, so the seat
    wins and you end up chamfering a foot recess instead of the case's rim.

    "Lowest plane" (most-negative perpendicular gap from the tent origin) is what lets this
    follow the skin: with BSKIN the true ground drops to the skin bottom, and the old wedge line
    survives only as tiny down-faces on the arm bottoms inside the gap pockets — those sit a
    whole BSKIN_GAP + BSKIN_THICK higher, so the skin plane wins. Foot-seat floors are cut UP
    into the material, so they too sit higher than the ground and never win."""
    origin, up = tent_plane()
    parallel = []
    for f in part.faces().filter_by(GeomType.PLANE):
        n = f.normal_at(f.center())
        if abs(n.Z + up[2]) > 0.02 or abs(n.Y + up[1]) > 0.02:
            continue                                  # not a down-face parallel to the tent plane
        c = f.center()
        gap = ((c.X - origin[0]) * up[0] + (c.Y - origin[1]) * up[1]
               + (c.Z - origin[2]) * up[2])
        parallel.append((gap, f))
    if not parallel:
        return None
    lo = min(gap for gap, _ in parallel)
    on_lowest = [f for gap, f in parallel if abs(gap - lo) < 1e-3]
    return max(on_lowest, key=lambda f: f.area)


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
    """Cutter: shallow Ø FOOT_DIA seats in the OUTER bottom face at FOOT_POSITIONS.

    Stick-on rubber feet locate in these seats at the 4 corners so the keyboard grips
    the desk. Each cylinder starts 0.5 mm outside the face (so it opens cleanly, no
    coincident face) and recesses FOOT_DEPTH into the material.

    The outer face is now the blind-port SKIN, a ``_skin_drop()`` below the wedge ground, so the
    seats are cut there. At the corners the skin is backed by solid case (the BSKIN_GAP pockets
    are local to the arms, mid-edge), so a FOOT_DEPTH seat keeps full backing — see the feet gate
    in .omc/specs/deep-dive-bottom-cover-inlay.md.

    Cut PERPENDICULAR to the tent plane, not plumb. The ground face is tilted, so a vertical
    cylinder would meet it obliquely — the seat depth would vary by ±0.17 mm across a Ø10 seat
    and the pad would sit on a slight ramp instead of flat against the desk.
    """
    _origin, up = tent_plane()
    seats = None
    for x, y in C.FOOT_POSITIONS:
        z = skin_ground_z(y)
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
    # ...and the band that actually SHOWS, outboard of both of those: out to the tub's skin and
    # flaring past it, starting where the visible band first gets taller than SEAM_REVEAL_H.
    # Added last of the three so it fuses onto a wedge that is already whole.
    bottom = cast(Part, bottom + _bottom_outer_shell())
    for hx, hy in C.MOUNTING_HOLES:
        cx, cy = C.pcb_to_case(hx, hy)
        bottom = cast(Part, bottom + stepped_standoff(at=(cx, cy)))

    bottom = cast(Part, bottom - battery_pocket())
    bottom = cast(Part, bottom - jst_pocket())
    bottom = cast(Part, bottom - jst_wire_channel())
    # Snap latches, cut into a whole bottom part BEFORE the skin caps it.
    #
    # They come after the wedge and outer band are fused because each arm's slot runs from the
    # ground face up to the ledge, so it has to cut a bottom part that is already whole — cut
    # earlier it would only free the plate's share of the wall and leave the arm rooted along its
    # whole bottom edge, which is the horizontal-axis bending this design exists to avoid.
    bottom = cast(Part, bottom - snap_reliefs())
    bottom = cast(Part, bottom + snap_barbs())
    # Blind-port skin: close the underside from below, then carve the air gap that keeps it off
    # every flexing arm. The skin caps the release ports (they vent into the gap, invisible from
    # outside) while the arms keep their full height, so no latch force moves. See
    # .omc/specs/deep-dive-bottom-cover-inlay.md.
    bottom = cast(Part, bottom + bottom_skin())
    bottom = cast(Part, bottom - snap_bottom_gap())
    # Feet and the ground-edge chamfer LAST, on the skin's outer face — the new ground.
    #
    # This is also why the chamfer moved after the snaps: it selects
    # ``ground_face(part).outer_wire().edges()``, and the ports used to break that wire into extra
    # edges (a 0.5 mm chamfer on the inside of a release port, 27.4 mm³ of stray cut). The skin's
    # face is unbroken — the ports no longer reach it — so the chamfer gets a clean rim.
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


def encoder_feature_top_z() -> float:
    """Case Z of the tallest COVER feature at the encoder — what the knob's hem must clear."""
    style = C.ENCODER_COVER_STYLE
    if style == "mound":
        return C.ENCODER_SHELL_TOP_Z
    if style in ("ring", "ring_bevel", "two_step"):
        return C.COVER_TOP_Z + C.ENCODER_RING_PROUD
    if style == "plinth":
        return C.ENCODER_PLINTH_TOP_Z
    if style == "racetrack":
        return C.COVER_TOP_Z + C.ENCODER_PAD_H
    return C.COVER_TOP_Z          # reveal / engraved / strokes add nothing proud


def _aperture_cutters(enc_cx: float, enc_cy: float, dia: float) -> list[Solid]:
    """Round the encoder window out to ``dia`` and chamfer its lip.

    The lip is cut with a CONE rather than found as an edge and chamfered: once the cover is fused
    the window rim sits among the membrane's other faces, which is exactly where OCC's edge-hunting
    gives up (the same reason the old mound needed a lid-stub to blend against)."""
    ch = C.ENCODER_APERTURE_CHAMFER
    z0 = C.MAIN_RIM_Z - 0.5
    bore = Solid.make_cylinder(dia / 2, encoder_feature_top_z() + 0.5 - z0).translate(
        (enc_cx, enc_cy, z0))
    lip = Solid.make_cone(dia / 2 + ch, dia / 2, ch).translate(
        (enc_cx, enc_cy, C.COVER_TOP_Z - ch))
    return [bore, lip]


def _engraved_circle(enc_cx: float, enc_cy: float) -> Part:
    """A groove CIRCLE round the knob, in the canopy strokes' own section (1.6 × 0.5): the knob
    gets a drawn ring without a single millimetre of proud material."""
    d, w = C.ENCODER_GROOVE_CIRCLE_DIA, C.ENCODER_GROOVE_W
    h = C.ENCODER_GROOVE_DEPTH + 0.2
    z0 = C.COVER_TOP_Z - C.ENCODER_GROOVE_DEPTH
    outer = Solid.make_cylinder((d + w) / 2, h).translate((enc_cx, enc_cy, z0))
    inner = Solid.make_cylinder((d - w) / 2, h).translate((enc_cx, enc_cy, z0))
    return cast(Part, outer - inner)


def _stroke_grooves(enc_cx: float, enc_cy: float, side: str) -> list[Part]:
    """PUZZLE LINE A's BASELINE, continued across the deck with the knob standing on it.

    This is not a stroke that imitates the roof's: ``canopy_puzzle.line_in_canopy`` hands back the
    same fitted line the canopy roofs' marks are drawn from. It is the BASELINE, though, not the
    mark — the roofs are cut with that line plus the lateral profile, and this groove is straight.
    Straight on purpose: the roof curve earns its bend from running across two splayed halves, and a
    3 mm bow in a 13 mm stub under a knob would read as a wobble rather than as the same gesture.
    It also keeps the deck groove's own width (``ENCODER_GROOVE_W``, still 1.6) legible where the
    roof's 1.0 would read as a scratch across bare deck. On the RIGHT half the line passes 6.10 mm
    from the
    encoder centre — inside the Ø13 knob's own 6.5 mm radius, so it genuinely runs under the knob
    and the knob interrupts it, the way each roof stroke runs off its edge and is picked up by the
    other half. The break is set by a keep-out CIRCLE, so the two stubs stop the same distance out
    instead of being nibbled unevenly by the aperture.

    ON THE LEFT HALF THERE IS NOTHING TO CONTINUE. The MCU is flipped there, so the canopy and its
    strokes sit elsewhere and the nearest line passes 26.1 mm from the encoder. Continuing it would
    not read as an interrupted stroke — it would be an unexplained groove across bare deck, drawn
    26 mm from the thing it is supposed to be about. So the half is skipped, and the treatment is
    honestly asymmetric rather than symmetrically meaningless."""
    a, b, c = PZ.line_in_canopy(side, 0)
    h = a * enc_cx + b * enc_cy - c                 # signed distance, centre → line
    px, py = enc_cx - a * h, enc_cy - b * h          # foot of the perpendicular
    dx, dy = -b, a                                   # unit direction along the line
    r = C.ENCODER_STROKE_KEEPOUT_R
    if abs(h) >= r:
        # The line misses the keep-out entirely, so the knob never interrupts it and the premise of
        # the style is gone. Cut nothing rather than a groove that means nothing.
        return []
    t_break = (r * r - h * h) ** 0.5
    run = C.ENCODER_STROKE_RUN
    w, depth = C.ENCODER_GROOVE_W, C.ENCODER_GROOVE_DEPTH
    height = depth + 0.2
    z_mid = C.COVER_TOP_Z - depth + height / 2
    ang = math.degrees(math.atan2(dy, dx))

    # The stroke must stay on the FLAT deck. Line A runs nearly north–south here, so its northern
    # arm would climb the canopy ramp, where a flat-bottomed cutter shaves a wedge out of the slope
    # instead of cutting a groove. Clip that arm at the ramp toe; in practice the clip lands inside
    # the knob's own keep-out, so what survives is a single stroke leaving the knob southward.
    from .canopy import CANOPY_RAMP_FOOT_Y
    y_limit = CANOPY_RAMP_FOOT_Y - 1.0

    out = []
    for sign in (+1, -1):
        reach = run
        if dy * sign > 0:                       # this arm heads north, toward the ramp
            reach = min(run, (y_limit - py) / (dy * sign))
        length = reach - t_break
        if length <= 0.5:                       # nothing worth cutting on this side
            continue
        t_mid = sign * (t_break + length / 2)
        out.append(cast(Part, Pos(px + dx * t_mid, py + dy * t_mid, z_mid)
                        * Rot(0, 0, ang) * Box(length, w, height)))
    return out


def _pad_capsule(enc_cx: float, enc_cy: float) -> Part:
    """A LOW capsule pad running from south of the encoder up to the canopy's ramp toe, so knob →
    pad → ramp read as one form.

    1.2 mm proud was chosen when the pad was believed to close the gap under the knob to ~0.5. It
    does not: the knob bottoms on its own bore at Z 21.4 regardless, leaving 3.8 mm of bare shaft
    over a 1.2 mm pad. Only the 4.5 mm mound reaches that hem. So this is a pad about the DECK's
    form — knob, pad, ramp as one silhouette — and it costs bare shaft to have it."""
    from .canopy import CANOPY_RAMP_FOOT_Y
    y0 = enc_cy - C.ENCODER_PAD_SOUTH
    y1 = CANOPY_RAMP_FOOT_Y + 1.0            # overlap the ramp toe so the two fuse
    w, length = C.ENCODER_PAD_W, y1 - y0
    with BuildSketch() as sk:
        RectangleRounded(w, length, w / 2 - 0.01)     # capsule
    base = cast(Face, sk.sketch.faces()[0].moved(
        Location((enc_cx, (y0 + y1) / 2, C.MAIN_RIM_Z))))
    pad = cast(Part, extrude(base, amount=C.COVER_THICKNESS + C.ENCODER_PAD_H))
    top_z = C.COVER_TOP_Z + C.ENCODER_PAD_H
    edge = [e for e in pad.edges() if abs(e.center().Z - top_z) < 0.05]
    if edge:
        try:
            pad = cast(Part, chamfer(edge, length=C.ENCODER_PAD_CHAMFER))
        except (ValueError, Standard_Failure):
            pass
    return pad


def _encoder_ring(enc_cx: float, enc_cy: float, *,
                  top_dia: float | None = None,
                  bevel_run: float | None = None,
                  bevel_drop: float | None = None,
                  groove: bool = True,
                  step: bool = False) -> Part:
    """SEALED bezel: circular, closed roof over the encoder body, bevelled top, shadow groove foot.

    The outer form is a SOLID OF REVOLUTION, not a cylinder with a chamfer hunted afterwards. That
    buys two things: the bevel can be asymmetric (a RUN and a DROP, so it can sit at the case's own
    26.6° instead of a generic 45°), and the treatment cannot silently fail the way an edge chamfer
    does when OCC dislikes the edge.

    THE DIAMETER IS SET BY THE BEVEL, not by taste. The cavity has to clear the EC11 body, so its
    rounded corners sit at r 8.92; the bevel eats ``bevel_run`` off the outside at the top; what is
    left between them is the wall that carries the roof at those four corners. Ø20.5 with the
    original 1.5 mm bevel leaves −0.17 — i.e. the bevel cut past the cavity and knife-edged the
    roof at the corners. The guard below refuses that."""
    top_dia = C.ENCODER_RING_TOP_DIA if top_dia is None else top_dia
    run = C.ENCODER_RING_BEVEL_RUN if bevel_run is None else bevel_run
    drop = C.ENCODER_RING_BEVEL_DROP if bevel_drop is None else bevel_drop
    proud = C.ENCODER_RING_PROUD
    top_z = C.COVER_TOP_Z + proud
    r_top = top_dia / 2
    r_out = r_top + run                       # base radius, derived from the top face

    # The guard has to measure the cavity THIS FUNCTION ACTUALLY CUTS, not the one constants.py
    # estimated at import time — that estimate is built on a hardcoded window size and can only
    # drift as the gerber-derived bbox moves. Same figures as the cavity sketch below.
    _, _, bbox_w, bbox_h = _encoder_bbox()
    cav_corner_r = math.hypot(
        (bbox_w + 2 * C.ENCODER_SHELL_CAVITY_CLEAR) / 2 - C.ENCODER_RING_CAVITY_R,
        (bbox_h + 2 * C.ENCODER_SHELL_CAVITY_CLEAR) / 2 - C.ENCODER_RING_CAVITY_R,
    ) + C.ENCODER_RING_CAVITY_R

    # TWO walls, binding at different heights, and both are load-bearing:
    #   ceiling — the roof is carried here, where the bevel has already flared out;
    #   foot    — the cavity is full width down here, so this is the thinner one on a steep bevel.
    # Checking only the ceiling let a Ø18.10 base through once, with 0.13 mm of wall at the corners.
    wall_ceiling = r_top + C.ENCODER_RING_ROOF * run / drop - cav_corner_r
    wall_foot = r_out - cav_corner_r
    if min(wall_ceiling, wall_foot) < 0.8:
        raise ValueError(
            f"ring top Ø{top_dia} with bevel {run}/{drop} leaves {wall_ceiling:.2f} mm of wall at "
            f"the cavity ceiling and {wall_foot:.2f} mm at the foot (cavity corners r "
            f"{cav_corner_r:.2f}); widen the ring or open the bevel")
    if drop > proud:
        raise ValueError(f"bevel drop {drop} exceeds the ring's own height {proud}")

    # Outer profile, axis → rim, base → bevelled top.
    with BuildPart() as bp:
        with BuildSketch(Plane.XZ) as sk:
            with BuildLine():
                Polyline((0.0, C.MAIN_RIM_Z),
                         (r_out, C.MAIN_RIM_Z),
                         (r_out, top_z - drop),
                         (r_top, top_z),
                         (0.0, top_z),
                         close=True)
            make_face()
        revolve(axis=Axis.Z)
    body = cast(Part, bp.part.translate((enc_cx, enc_cy, 0)))

    if step:
        tier = cast(Part, Solid.make_cylinder(
            C.ENCODER_STEP_DIA / 2,
            C.COVER_THICKNESS + C.ENCODER_STEP_H).translate((enc_cx, enc_cy, C.MAIN_RIM_Z)))
        tier_top = C.COVER_TOP_Z + C.ENCODER_STEP_H
        edge = [e for e in tier.edges() if abs(e.center().Z - tier_top) < 0.05]
        if edge:
            try:
                tier = cast(Part, chamfer(edge, length=C.ENCODER_STEP_CHAMFER))
            except (ValueError, Standard_Failure):
                pass
        body = cast(Part, body + tier)

    cav_w = bbox_w + 2 * C.ENCODER_SHELL_CAVITY_CLEAR
    cav_h = bbox_h + 2 * C.ENCODER_SHELL_CAVITY_CLEAR
    cav_z0, cav_z1 = C.MAIN_RIM_Z - 0.2, top_z - C.ENCODER_RING_ROOF
    with BuildSketch() as sk:
        RectangleRounded(cav_w, cav_h, C.ENCODER_RING_CAVITY_R)
    cavity = extrude(cast(Face, sk.sketch.faces()[0].moved(Location((enc_cx, enc_cy, cav_z0)))),
                     amount=cav_z1 - cav_z0)
    shaft = Solid.make_cylinder(C.ENCODER_SHAFT_HOLE_DIA / 2, top_z - cav_z1 + 0.4).translate(
        (enc_cx, enc_cy, cav_z1 - 0.2))
    ring = cast(Part, body - cavity - shaft)

    if groove and C.ENCODER_RING_FOOT_GROOVE_H > 0 and C.ENCODER_RING_FOOT_GROOVE_D > 0:
        # A shadow line where the ring meets the deck, so the ring reads as a separate object
        # standing on the cover — the trick the case already uses at its own skirt. It prints as a
        # 0.5 mm outward step: the TOP part goes on the bed face-down, so this is a short overhang
        # near the bed, not a bridge over air.
        gh, gd = C.ENCODER_RING_FOOT_GROOVE_H, C.ENCODER_RING_FOOT_GROOVE_D
        outer = Solid.make_cylinder(r_out + 1.0, gh).translate((enc_cx, enc_cy, C.COVER_TOP_Z))
        inner = Solid.make_cylinder(r_out - gd, gh).translate((enc_cx, enc_cy, C.COVER_TOP_Z))
        ring = cast(Part, ring - cast(Part, outer - inner))
    return ring


ENCODER_COVER_STYLES = ("mound", "ring", "ring_bevel", "two_step", "plinth",
                        "reveal", "engraved", "strokes", "racetrack")


def apply_encoder_cover_style(top: Part, side: str = "right") -> Part:
    """Add/cut the encoder treatment on the fused TOP, per ``C.ENCODER_COVER_STYLE``.

    Only "mound" seats the knob without trimming its shaft — see the seating table in
    ``constants.py`` and ``knob.knob_seating_report()``. The rest are aesthetic choices that buy
    their look with bare shaft on show."""
    style = C.ENCODER_COVER_STYLE
    # Validated up front: the old check sat after the sealed branch had already returned and after
    # the racetrack pad had been fused, so a typo'd style could do work before being rejected.
    if style not in ENCODER_COVER_STYLES:
        raise ValueError(f"unknown ENCODER_COVER_STYLE {style!r}; expected one of "
                         f"{', '.join(ENCODER_COVER_STYLES)}")
    if style == "mound":
        return cast(Part, top + _encoder_shell())

    enc_cx, enc_cy, _, _ = _encoder_bbox()

    if style == "plinth":
        # Sealed, so no aperture cut, for the same reason as the ring below: the skin lands on the
        # cover just outside the window and boring first would undercut what it stands on.
        return cast(Part, top + _encoder_plinth(enc_cx, enc_cy))

    if style in ("ring", "ring_bevel", "two_step"):
        # NO aperture cut for the sealed styles: the ring's wall lands on the cover just outside
        # the Ø17.91 window, and boring the aperture first undercuts what it stands on.
        if style == "ring_bevel":
            return cast(Part, top + _encoder_ring(enc_cx, enc_cy))
        # "ring" / "two_step" keep the plain symmetric 45° edge and no foot groove.
        return cast(Part, top + _encoder_ring(
            enc_cx, enc_cy, top_dia=C.ENCODER_RING_BASE_DIA - 2 * C.ENCODER_RING_CHAMFER,
            bevel_run=C.ENCODER_RING_CHAMFER, bevel_drop=C.ENCODER_RING_CHAMFER,
            groove=False, step=(style == "two_step")))

    if style == "racetrack":
        # Pad first, aperture second — it is a solid capsule and has to be bored through together
        # with the cover, or its centre stays filled.
        top = cast(Part, top + _pad_capsule(enc_cx, enc_cy))

    dia = C.ENCODER_REVEAL_DIA if style == "reveal" else C.ENCODER_APERTURE_DIA
    for cutter in _aperture_cutters(enc_cx, enc_cy, dia):
        top = cast(Part, top - cutter)

    if style == "engraved":
        top = cast(Part, top - _engraved_circle(enc_cx, enc_cy))
    elif style == "strokes":
        for groove in _stroke_grooves(enc_cx, enc_cy, side):
            top = cast(Part, top - groove)
    return top


def _encoder_plinth(enc_cx: float, enc_cy: float) -> Part:
    """SEALED bezel that is a rounded SQUARE at the deck and a small CIRCLE at the top.

    Two ideas, and both exist to answer "the ring under the knob is too large":

    THE SKIN FOLLOWS THE CAVITY. The cavity is square, so its corners sit further out than its
    flats. A circular bezel has to reach those corners in EVERY direction, which is the entire
    reason the sealed ring is Ø19.5 — across its flats it carries ~3 mm/side of material spanning
    corners that are somewhere else. A square skin hugs the square, and the flats come in by
    2.2 mm/side for the same wall thickness.

    THE CAVITY STEPS IN ABOVE THE LEG. The top can only be small if there is nothing wide left to
    roof. Below ``ENCODER_PLINTH_STEP_Z`` the cavity has to clear the whole EC11 including its
    locating leg; above it, the only occupant is the Ø6 shaft, so the bezel necks to a circle that
    fits under the knob. The sealed-ring round concluded a hidden bezel was impossible — it was
    impossible only while the cavity ran full height.

    The morph is 45° across the flats and ~74° at the corners (a square cannot become a circle in
    a fixed height without the corners travelling further). Every section shrinks going up, so the
    whole thing is self-supporting printed bezel-up; ``test_the_plinth_only_ever_shrinks_going_up``
    is what actually holds that, not this docstring."""
    _, _, bbox_w, bbox_h = _encoder_bbox()
    clr = C.ENCODER_SHELL_CAVITY_CLEAR
    cav_w, cav_h = bbox_w + 2 * clr, bbox_h + 2 * clr
    out_w = cav_w + 2 * C.ENCODER_PLINTH_WALL
    out_h = cav_h + 2 * C.ENCODER_PLINTH_WALL

    # Guard on the cavity THIS FUNCTION CUTS, not on constants' import-time estimate — the same
    # discipline _encoder_ring uses, and for the same reason: the estimate is built on a hardcoded
    # window size and can only drift as the gerber-derived bbox moves.
    cav_r, skin_r = C.ENCODER_PLINTH_CAVITY_R, C.ENCODER_PLINTH_CORNER_R
    cav_corner = math.hypot(cav_w / 2 - cav_r, cav_h / 2 - cav_r) + cav_r
    # Thinnest wall is the cavity's corner POINT against the skin's corner ARC, not the diagonal
    # gap — see the note in constants.py. While the arc stays within the wall the binding point is
    # on a flat instead, and the wall is just the wall.
    wall = (C.ENCODER_PLINTH_WALL if skin_r <= C.ENCODER_PLINTH_WALL
            else skin_r - (skin_r - C.ENCODER_PLINTH_WALL) * math.sqrt(2))
    if wall < C.ENCODER_PLINTH_WALL:
        raise ValueError(
            f"skin rounding R{skin_r} cuts the wall at the cavity's corner points to {wall:.2f} mm "
            f"(need {C.ENCODER_PLINTH_WALL}); crisper skin corners or a wider ENCODER_PLINTH_WALL")
    # The cavity is SQUARE on purpose: rounding a concave corner refills it, straight at the
    # corners of the steel box it exists to clear.
    if cav_corner - 8.768 <= 0.5:
        raise ValueError(
            f"cavity corners reach r {cav_corner:.2f}, only {cav_corner - 8.768:.2f} mm clear of "
            f"the EC11 body's corners — do not round ENCODER_PLINTH_CAVITY_R")

    shoulder_z, top_z = C.ENCODER_PLINTH_SHOULDER_Z, C.ENCODER_PLINTH_TOP_Z

    # Deck → shoulder as ONE straight taper. There is no vertical stretch: the whole wall is the
    # chamfer, so the bezel is a square frustum standing in the cover rather than a box with a
    # broken edge. A 0.8 mm foot chamfer was tried first and could not be seen against a 3.4 mm
    # wall.
    #
    # BUILT, not hunted. Chamfering this after the bezel is fused into the lid is precisely what
    # OCC cannot be relied on to do — the edge sits among the membrane's other faces (fuse margin,
    # neighbouring windows), which is why the mound needs a lid-stub to give its foot fillet a
    # clean local surface to roll onto. Same discipline as _encoder_ring's revolve and the
    # shoulder→circle loft below.
    flare = C._plinth_taper_flare
    foot_w, foot_h = out_w + 2 * flare, out_h + 2 * flare
    foot_r = C.ENCODER_PLINTH_CORNER_R + flare

    def _rr(w, h, r, z):
        with BuildSketch(Plane.XY.offset(z)) as _sk:
            RectangleRounded(w, h, r)
        return cast(Face, _sk.sketch.faces()[0])

    # 1. buried skirt, MAIN_RIM_Z → deck, at the full foot section
    body = cast(Part, extrude(
        cast(Face, _rr(foot_w, foot_h, foot_r, 0.0).moved(
            Location((enc_cx, enc_cy, C.MAIN_RIM_Z)))),
        amount=C.COVER_TOP_Z - C.MAIN_RIM_Z))
    # 2. the taper, deck → shoulder
    taper = loft([_rr(foot_w, foot_h, foot_r, C.COVER_TOP_Z),
                  _rr(out_w, out_h, C.ENCODER_PLINTH_CORNER_R, shoulder_z)])
    body = cast(Part, body + cast(Part, taper.moved(Location((enc_cx, enc_cy, 0)))))

    # The morph. A LOFT between the square shoulder and the circular top, not a chamfer hunted on
    # the finished solid: there is no edge to chamfer between a square and a circle, and OCC's
    # edge-hunting is exactly what fails once this is fused into the lid's other faces.
    with BuildSketch(Plane.XY.offset(shoulder_z)) as sk_lo:
        RectangleRounded(out_w, out_h, C.ENCODER_PLINTH_CORNER_R)
    with BuildSketch(Plane.XY.offset(top_z)) as sk_hi:
        Circle(C.ENCODER_PLINTH_TOP_DIA / 2)
    cap = loft([cast(Face, sk_lo.sketch.faces()[0]), cast(Face, sk_hi.sketch.faces()[0])])
    body = cast(Part, body + cast(Part, cap.moved(Location((enc_cx, enc_cy, 0)))))

    # Stepped cavity: full section up to the leg, shaft bore above it.
    with BuildSketch() as sk_cav:
        if cav_r > 0:
            RectangleRounded(cav_w, cav_h, cav_r)
        else:
            Rectangle(cav_w, cav_h)      # square — RectangleRounded rejects a zero radius
    cav_z0 = C.MAIN_RIM_Z - 0.2
    cavity = extrude(cast(Face, sk_cav.sketch.faces()[0].moved(
        Location((enc_cx, enc_cy, cav_z0)))), amount=C.ENCODER_PLINTH_STEP_Z - cav_z0)
    shaft = Solid.make_cylinder(
        C.ENCODER_SHAFT_HOLE_DIA / 2,
        top_z - C.ENCODER_PLINTH_STEP_Z + 0.6).translate(
            (enc_cx, enc_cy, C.ENCODER_PLINTH_STEP_Z - 0.2))
    return cast(Part, body - cavity - shaft)


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
    tub = seam_skirt_tub()
    top = _chamfer_pocket_mouth(tub)   # tub-side starter chamfer at the pocket mouth
    # Carry the skin down to the desk over the southern stretch, so the front of the case
    # reads as one piece and the bottom wedge only shows further north. Costs no height.
    # The UN-chamfered tub is what the skirt is sectioned from. _chamfer_pocket_mouth opens the
    # mouth bore by SEAM_POCKET_LEAD_IN at exactly Z=0, which is exactly where the section is
    # taken, so the chamfered tub hands back a bore already set back 0.4 mm — and the channel's
    # lead-in then measures 0.2 instead of SEAM_LEAD_IN's 0.6, the two starters cancelling. The
    # mouth chamfer is a feature of the pocket, not of the wall, and must not run down the skirt.
    top = cast(Part, top + skirt_extension(tub))
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
    # Gated, because this one is not a no-op when the parting line stays at or below Z=0:
    # skirt_extension only ever subtracts the relief from its own band, all of it below Z=0, and
    # taking it off the whole tub would additionally shave the 0.1 mm of pocket wall the stock
    # reaches above Z=0. Small (~7 mm³) and harmless, but it would mean a flat parting line no
    # longer reproduces the un-dialled case.
    #
    # The gate asks the PROFILE, not the dial. `SEAM_NORTH_RISE_Z > 0.0` answered the same
    # question only while the northern run was the high point of the curve — any other way of
    # climbing above Z=0 got no relief and no failure. See seam_profile_max_z.
    if seam_profile_max_z() > 0.0:
        top = cast(Part, top - _lead_in_relief(wedge_deep_z() - 1.0))
    top = cast(Part, top + build_top_cover(fuse_margin=C.COVER_FUSE_MARGIN))
    top = apply_encoder_cover_style(top, side)
    top = cast(Part, top + build_canopy(side=side))
    # USB port re-cut AFTER the fuse: the flipped half's port floor sits below COVER_TOP_Z, so
    # the cover backfills the bottom of the window otherwise. See canopy.usb_port_cutter.
    top = cast(Part, top - usb_port_cutter(side))
    # Slide-switch finger scoop: cut AFTER the canopy fuse so it lowers the wall + cover together.
    top = cast(Part, top - _slide_scoop())
    # Slide-switch drop-in pocket: registered switch-shaped cavity.
    top = cast(Part, top - _slide_actuator_cavity())
    # Catch pockets for the snap latches, blind notches in the skirt's INNER face. Cut last of
    # the TOP's rabbet features and after _below_seam_cutter, so a pocket can never survive on
    # skin the parting line has already taken away.
    top = cast(Part, top - snap_catches())
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
