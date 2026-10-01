"""Assembled slide-switch finger access and flat-wall guarantees."""
from functools import cache

import pytest
from build123d import (
    Axis,
    Box,
    BuildPart,
    BuildSketch,
    Ellipse,
    Location,
    Locations,
    Plane,
    Pos,
    Solid,
    extrude,
    mirror,
)

from sofle_case import constants as C
from sofle_case.pcb_geometry import rotate_2d, slide_switch_placement
from tests.shared_builds import build_case_half, build_mcu_encoder_cover, build_tray

# The unchanged hardware phantom already contains the complete travel block.
_COLLISION_TOL = 1e-5


def _sided(part, side):
    if side == "right":
        return part
    return Pos(C.OUTER_WIDTH / 2, 0, 0) * mirror(
        Pos(-C.OUTER_WIDTH / 2, 0, 0) * part, about=Plane.YZ
    )


def _nub_center():
    cx, cy, rot = slide_switch_placement()
    dx, dy = rotate_2d(
        C.SLIDE_ACTUATOR_PIN_CENTER_X,
        -(C.SLIDE_ACTUATOR_BODY_W / 2 + C.SLIDE_ACTUATOR_NUB_D / 2),
        rot,
    )
    return cx + dx, cy + dy


def _switch_can():
    cx, cy, rot = slide_switch_placement()
    dx, dy = rotate_2d(C.SLIDE_ACTUATOR_PIN_CENTER_X, 0.0, rot)
    with BuildPart() as bp, Locations(Location(
        (cx + dx, cy + dy, C.PCB_TOP_Z + C.SLIDE_ACTUATOR_BODY_H / 2),
        (0, 0, rot),
    )):
        Box(C.SLIDE_ACTUATOR_BODY_L, C.SLIDE_ACTUATOR_BODY_W,
            C.SLIDE_ACTUATOR_BODY_H)
    return bp.part


@pytest.mark.parametrize("side", ["right", "left"])
def test_complete_actuator_phantom_clears_printed_parts(side):
    from sofle_case.pcb_phantom import _slide_switch_body

    hardware = _sided(_slide_switch_body(), side)
    for name, part in (("case", build_case_half(side)),
                       ("cover", build_mcu_encoder_cover(side))):
        assert (part & hardware).volume <= _COLLISION_TOL, (
            f"{side} {name} collides with the unchanged full-travel phantom"
        )
        assert part.distance_to(hardware) >= 0.3 - 1e-5


@pytest.mark.parametrize("side", ["right", "left"])
def test_concave_return_screens_switch_can_at_inner_wall(side):
    can = _switch_can().bounding_box()
    _, ny = _nub_center()
    inner_wall = C.pcb_to_case(0, 0)[0] - C.PCB_XY_CLEARANCE
    shield = Solid.make_box(0.1, can.size.Y, can.size.Z).translate(
        (inner_wall - 0.2, can.min.Y, can.min.Z))
    # Protect the can's outer silhouette behind the curved return, not a
    # back plate or another actuator-sized hole at the finger contact face.
    window = Solid.make_box(0.3, 6.5, 4.0).translate(
        (inner_wall - 0.3, ny - 3.25, C.SLIDE_NUB_Z - 1.8))
    assembled = build_case_half(side) + build_mcu_encoder_cover(side)
    assert (_sided(shield - window, side) - assembled).volume <= _COLLISION_TOL


@cache
def _finger_approach_envelope():
    """Localized 5 x 4 mm pad contact, not clearance for an entire finger.

    Only contact shifts over the existing block's face; hardware is unchanged.
    Homothety 1.15 encloses >=0.3 mm growth since the minimum pad radius is 2.
    This is a geometric contact probe, not a claim about finger anatomy.
    """
    nx, ny = _nub_center()
    half = C.SLIDE_ACTUATOR_NUB_L / 2
    x0 = build_case_half("right").bounding_box().min.X - 10
    x1 = nx - C.SLIDE_ACTUATOR_NUB_D / 2 + 0.3
    with BuildPart() as ends:
        with BuildSketch(Plane.YZ), Locations(
            (ny - half, C.SLIDE_NUB_Z), (ny + half, C.SLIDE_NUB_Z)
        ):
            Ellipse(2.875, 2.3)
        extrude(amount=x1 - x0)
    middle = Solid.make_box(x1 - x0, 2 * half, 4.6).translate(
        (x0, ny - half, C.SLIDE_NUB_Z - 2.3))
    return Pos(x0, 0, 0) * ends.part + middle


@pytest.mark.parametrize("side", ["right", "left"])
def test_localized_pad_reaches_travel_face_with_cover_installed(side):
    envelope = _sided(_finger_approach_envelope(), side)
    for part in (build_case_half(side), build_mcu_encoder_cover(side)):
        assert (part & envelope).volume <= _COLLISION_TOL


@pytest.mark.parametrize("side", ["right", "left"])
def test_mounted_cover_has_relief_above_the_actuator_approach(side):
    from sofle_case.mcu_encoder_cover import _shell

    nx, ny = _nub_center()
    front = nx - C.SLIDE_ACTUATOR_NUB_D / 2
    clearance = _sided(Solid.make_box(0.6, 6.0, 0.4).translate(
        (front - 0.6, ny - 3.0, C.MAIN_RIM_Z + 0.2)), side)
    assert (_sided(_shell(side), side) & clearance).volume > 1.0
    assert (build_mcu_encoder_cover(side) & clearance).volume <= _COLLISION_TOL


def test_neg_x_wall_flat_at_mcu():
    """No hill: the −X wall over the MCU is flat at MAIN_RIM_Z, not raised."""
    tray = build_tray()
    _, mcu_cy = C.pcb_to_case(*C.MCU_POS)
    # At MCU Y the polygon left edge is the (0,0)→(0,-80.5) segment (PCB X=0),
    # not PCB_X_MIN which only applies at the board's bottom corners.
    poly_left_x = C.pcb_to_case(0.0, 0.0)[0]
    wall_center_x = poly_left_x - (C.WALL_THICKNESS + C.PCB_XY_CLEARANCE) / 2
    probe_z = C.MAIN_RIM_Z - 0.5
    probe = Solid.make_box(2.0, 2.0, 0.3).translate(
        (wall_center_x - 1.0, mcu_cy - 1.0, probe_z)
    )
    vol = (tray & probe).volume
    assert vol > 0.01, (
        "−X wall has no material at MCU Y just below rim — wall may not reach MAIN_RIM_Z"
    )
    above_probe = Solid.make_box(2.0, 2.0, 0.3).translate(
        (wall_center_x - 1.0, mcu_cy - 1.0, C.MAIN_RIM_Z + 0.2)
    )
    above_vol = (tray & above_probe).volume
    assert above_vol < 0.01, (
        "−X wall over MCU has material above rim — wall is not flat at MAIN_RIM_Z"
    )


def test_no_wall_above_rim():
    """All walls are flat at MAIN_RIM_Z — no feature (hill/ramp/relief) rises above it."""
    tray = build_tray()
    high = tray.edges().filter_by_position(Axis.Z, minimum=C.MAIN_RIM_Z + 0.5, maximum=999)
    assert len(high) == 0, f"{len(high)} edges above the rim — walls are not flat"


@pytest.mark.parametrize("side", ["right", "left"])
def test_finger_recess_preserves_continuous_two_millimetre_floor(side):
    from sofle_case.slide_access import slide_finger_cutout

    bb = slide_finger_cutout().bounding_box()
    outer_wall = C.pcb_to_case(0, 0)[0] - C.WALL_THICKNESS - C.PCB_XY_CLEARANCE
    inner_wall = C.pcb_to_case(0, 0)[0] - C.PCB_XY_CLEARANCE
    x0, x1 = max(outer_wall, bb.min.X), min(inner_wall, bb.max.X)
    # A full 2 mm slab immediately below the lowest recess floor must remain
    # solid over the entire material-bearing wall footprint, not a point probe
    # or a floor-above-PCB datum. Higher rounded floor regions have more web.
    floor = Solid.make_box(x1 - x0, bb.size.Y, 2.0).translate(
        (x0, bb.min.Y, bb.min.Z - 2.0)
    )
    assert (_sided(floor, side) - build_case_half(side)).volume <= _COLLISION_TOL


@pytest.mark.parametrize("side", ["right", "left"])
def test_finger_recess_preserves_base_above_actual_faceted_underside(side):
    from sofle_case.slide_access import slide_finger_cutout

    bb = slide_finger_cutout().bounding_box()
    footprint = Solid.make_box(bb.size.X, bb.size.Y, C.MAIN_RIM_Z + 1).translate(
        (bb.min.X, bb.min.Y, 0)
    )
    tray = build_tray()
    # Translation difference measures the bottom 2 mm from the actual
    # external underside, including boat facets, throughout the access area.
    bottom_web = (tray - tray.translate((0, 0, 2.0))) & footprint
    assert (_sided(bottom_web, side) - build_case_half(side)).volume <= _COLLISION_TOL
