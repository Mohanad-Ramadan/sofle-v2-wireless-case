"""PCB phantom for visual fit-check in the OCP viewer.

Select it with ``scripts/build.py --phantoms``.
"""
from __future__ import annotations

from typing import cast

from build123d import (
    Box,
    BuildLine,
    BuildPart,
    BuildSketch,
    Cylinder,
    Location,
    Locations,
    Mode,
    Part,
    Plane,
    Polyline,
    Pos,
    Wire,
    extrude,
    make_face,
)

from . import constants as C
from .pcb_geometry import polygon_in_case_coords, rotate_2d, slide_switch_placement

# SW31 pin holes from SofleKeyboard-PTH.drl (inch→mm). All at PCB X≈2.944.
_SW31_PIN_HOLES: tuple[tuple[float, float, float], ...] = (
    # (pcb_x_mm, pcb_y_mm, drill_dia_mm)
    (0.1159 * 25.4, -1.6192 * 25.4, 0.0591 * 25.4),  # mounting
    (0.1159 * 25.4, -1.7019 * 25.4, 0.0315 * 25.4),  # signal (ref point)
    (0.1159 * 25.4, -1.7806 * 25.4, 0.0315 * 25.4),  # signal
    (0.1159 * 25.4, -1.8594 * 25.4, 0.0315 * 25.4),  # signal
    (0.1159 * 25.4, -1.9420 * 25.4, 0.0591 * 25.4),  # mounting
)


def _slide_switch_pin_holes() -> Part:
    """SW31 PTH pin holes as cylinders through PCB thickness for visual confirmation."""
    with BuildPart() as bp:
        for pcb_x, pcb_y, dia in _SW31_PIN_HOLES:
            cx, cy = C.pcb_to_case(pcb_x, pcb_y)
            with Locations((cx, cy, C.PCB_SEAT_Z + C.PCB_THICKNESS / 2)):
                Cylinder(radius=dia / 2, height=C.PCB_THICKNESS + 0.02)
    assert bp.part is not None
    return bp.part


def _pcb_plate() -> Part:
    """PCB polygon extruded from PCB_SEAT_Z to PCB_TOP_Z, M2 holes subtracted."""
    poly = polygon_in_case_coords()
    pts = poly[:-1] if poly[0] == poly[-1] else poly

    with BuildLine() as bl:
        Polyline(*pts, close=True)
    wire = cast(Wire, bl.line)

    with BuildPart() as bp:
        with BuildSketch(Plane.XY):
            make_face(wire)  # type: ignore[arg-type]
        extrude(amount=C.PCB_THICKNESS)
        for hx, hy in C.MOUNTING_HOLES:
            cx, cy = C.pcb_to_case(hx, hy)
            with Locations((cx, cy, C.PCB_THICKNESS / 2)):
                Cylinder(
                    radius=C.PCB_HOLE_DIA / 2,
                    height=C.PCB_THICKNESS + 0.1,
                    mode=Mode.SUBTRACT,
                )

    assert bp.part is not None
    return cast(Part, Pos(0, 0, C.PCB_SEAT_Z) * bp.part)


def _mcu_block() -> Part:
    """nice!nano on long headers — board-only box plus thin pin rails (tall-header split).

    Reality: MCU sits on ~11 mm headers, bottom at C.MCU_PCB_BOT_Z (20.1) well
    above MAIN_RIM_Z (15.7) — 4.4 mm air. Between PCB and MCU there are only
    thin pin columns in open air, no full-width block at wall height. The old
    solid block (PCB_TOP_Z → MCU_PCB_TOP_Z, 11 mm, full footprint) over-claimed
    wall-level volume and falsely intersected the strict PCB-frame wall.

    Split: board box [MCU_PCB_BOT_Z → MCU_PCB_TOP_Z] (1.6 mm thick, full
    MCU_WIDTH × BODY_L footprint) plus two thin pin rails (~0.64 mm square,
    2.54 mm pitch rows approx.) from PCB_TOP_Z → MCU_PCB_BOT_Z at the MCU
    east/west edges, clipped inside the inner cavity so they never intersect
    the strict wall. USB stub stays above rim and is unchanged.
    """
    cx, _ = C.pcb_to_case(*C.MCU_POS)
    # Anchored at the pin array (MCU_BODY_N_Y), not centred on MCU_POS — the board's extra
    # length over a Pro Micro is at the SOUTH end. See constants.MCU_BODY_N_Y.
    center_y = (C.MCU_BODY_N_Y + C.MCU_BODY_S_Y) / 2

    # Board-only box — the actual PCB, above the rim.
    board_h = C.MCU_PCB_TOP_Z - C.MCU_PCB_BOT_Z  # 1.6 mm
    board_center_z = (C.MCU_PCB_BOT_Z + C.MCU_PCB_TOP_Z) / 2

    # Pin rails — thin columns in open air below the board. Must stay inside
    # the strict inner cavity, so clipped south of the north wall's inner face.
    # Using two continuous rails at the east/west edges as an approximation for
    # the two 2.54 mm pitch pin rows (≈0.64 mm square each).
    pin_h = C.MCU_PCB_BOT_Z - C.PCB_TOP_Z
    pin_center_z = (C.PCB_TOP_Z + C.MCU_PCB_BOT_Z) / 2
    pin_w = 0.64  # ~0.64 mm square pin
    # East/west X at MCU edges, inset by half pin width so rail stays inside MCU footprint
    # and well inside PCB polygon's cavity.
    east_x = cx + C.MCU_WIDTH / 2 - pin_w / 2 - 0.1
    west_x = cx - C.MCU_WIDTH / 2 + pin_w / 2 + 0.1
    # Clip Y to stay inside strict wall inner face — north wall inner is
    # pcb_to_case(0,0)[1] + CLEARANCE. Keep 0.3 mm clearance inside cavity.
    inner_north = C.pcb_to_case(0, 0)[1] + C.PCB_XY_CLEARANCE - 0.3
    rail_y0 = C.MCU_BODY_S_Y
    rail_y1 = min(C.MCU_BODY_N_Y, inner_north)
    rail_len = rail_y1 - rail_y0
    rail_center_y = (rail_y0 + rail_y1) / 2

    with BuildPart() as bp:
        # Board
        with Locations((cx, center_y, board_center_z)):
            Box(C.MCU_WIDTH, C.MCU_BODY_L, board_h)
        # Pin rails — only if there is positive length inside cavity
        if rail_len > 0 and pin_h > 0:
            with Locations((west_x, rail_center_y, pin_center_z)):
                Box(pin_w, rail_len, pin_h)
            with Locations((east_x, rail_center_y, pin_center_z)):
                Box(pin_w, rail_len, pin_h)

    assert bp.part is not None
    return bp.part


def _usb_c_stub(side: str = "right") -> Part:
    """USB-C jack body stub at the +Y face of the MCU block, at this half's measured band.

    The stub protrudes ``C.USB_JACK_Y_PROTRUDE`` (1.0 mm, measured) past the board's +Y
    edge — the real jack stops 0.57 mm short of the case north wall's inner face, so
    the viewer shows that air gap (only the plug bridges the wall). It was a 7.0 mm
    tongue that poked ~1.6 mm PAST the wall's outer face — a visual lie. On the FLIPPED
    half the jack hangs under the nano board: its Z band (17.64→20.80) falls inside
    ``_mcu_block``'s Z span, so only the 1.0 mm tongue shows there — expected."""
    cx, _ = C.pcb_to_case(*C.MCU_POS)
    mcu_y_face = C.MCU_BODY_N_Y           # +Y (USB-end) face of the board = 117.18 case-Y
    stub_center_y = mcu_y_face + C.USB_JACK_Y_PROTRUDE / 2
    jack_lo, jack_hi = C.usb_jack_z(side)
    stub_h = jack_hi - jack_lo
    center_z = jack_lo + stub_h / 2

    with BuildPart() as bp, Locations((cx, stub_center_y, center_z)):
        Box(C.USB_C_W, C.USB_JACK_Y_PROTRUDE, stub_h)

    assert bp.part is not None
    return bp.part


def _slide_switch_body() -> Part:
    """SK12D07VG3 metal can + actuator nub, placed via components.json rotation.

    Local frame: pins along local X, body centered over pin span.
    Actuator nub extends in local -Y (toward -X wall after 270° rotation).
    """
    cx, cy, rot = slide_switch_placement()

    body_z = C.PCB_TOP_Z + C.SLIDE_ACTUATOR_BODY_H / 2

    bdx, bdy = rotate_2d(C.SLIDE_ACTUATOR_PIN_CENTER_X, 0.0, rot)
    ndx, ndy = rotate_2d(
        C.SLIDE_ACTUATOR_PIN_CENTER_X,
        -(C.SLIDE_ACTUATOR_BODY_W / 2 + C.SLIDE_ACTUATOR_NUB_D / 2),
        rot,
    )

    with BuildPart() as bp:
        with Locations(Location((cx + bdx, cy + bdy, body_z), (0, 0, rot))):
            Box(C.SLIDE_ACTUATOR_BODY_L, C.SLIDE_ACTUATOR_BODY_W,
                C.SLIDE_ACTUATOR_BODY_H)
        with Locations(Location((cx + ndx, cy + ndy, C.SLIDE_NUB_Z), (0, 0, rot))):
            Box(C.SLIDE_ACTUATOR_NUB_L, C.SLIDE_ACTUATOR_NUB_D,
                C.SLIDE_ACTUATOR_NUB_H)

    assert bp.part is not None
    return bp.part


def _jst_body(mount: str = "east") -> Part:
    """Battery JST at J2 (S2B-XH-A-1, side entry) with its mated plug — hung UNDER the PCB.

    The connector is clearance-critical, so the phantom includes both the body and mated plug.

    It now hangs below ``PCB_SEAT_Z`` like the hotswap sockets, into a floor pocket. The plug is
    drawn too, at the full body section rather than its true smaller housing: this box is a
    CLEARANCE ENVELOPE and the pocket is blind with ample material under it.

    The JST envelope and its structural pocket use the same constants, so the phantom cannot
    drift from the clearance geometry.

    No ``JST_ROT``: the CPL rotation describes the 1x03 socket originally footprinted at J2, not
    the XH re-soldered underneath. ``JST_BODY_W``/``JST_BODY_D`` name their case axes directly, so
    applying a stale placement angle on top would rotate the envelope off the part it represents.

    Placement comes from ``battery.jst_body_center`` — the same function the pocket is cut from,
    deliberately. When this drew itself from ``JST_POS`` and the pocket did too, both were wrong
    together and agreed perfectly: the body sat 2.5 mm west of its own pins and no clash check
    could see it. One source or the phantom stops being evidence.

    ``mount`` picks which pair of holes the connector sits on. Both are electrically valid (the
    middle hole is B+, both outer holes GND), and the pocket is cut to span either — so this
    draws ONE of two legal positions. A clash check against this phantom alone therefore only
    proves the drawn one fits.
    """
    from .battery import jst_body_center
    cx, cy = jst_body_center(mount)
    body_z = C.JST_BOTTOM_Z + C.JST_BODY_H / 2
    plug_y = cy + C.JST_BODY_D / 2 + C.JST_PLUG_RUN / 2   # plug enters from the NORTH

    with BuildPart() as bp:
        with Locations((cx, cy, body_z)):
            Box(C.JST_BODY_W, C.JST_BODY_D, C.JST_BODY_H)
        with Locations((cx, plug_y, body_z)):
            Box(C.JST_BODY_W, C.JST_PLUG_RUN, C.JST_BODY_H)

    assert bp.part is not None
    return bp.part


def build_pcb_phantom(side: str = "right", include_encoder: bool = True) -> Part:
    """PCB plate + MCU daughter board + USB-C jack stub + slide-switch body + pin holes + EC11 & knob.

    ``side`` picks the MCU orientation, which sets where the jack stub sits in Z.

    The EC11 is included by default because it IS board hardware, and until now it was the one
    component with no phantom anywhere: ``switch_phantom`` skips SW25 on purpose (it is not an MX
    switch) and this module never picked it up, so the encoder was invisible in every fit-check.
    Pass ``include_encoder=False`` if something else in the scene already draws it."""
    children = [_pcb_plate(), _mcu_block(), _usb_c_stub(side),
                _slide_switch_body(), _slide_switch_pin_holes(), _jst_body()]
    if include_encoder:
        from .encoder_phantom import build_encoder_phantom
        children.append(build_encoder_phantom())      # EC11 + its knob
    return Part(children=children)


if __name__ == "__main__":
    from ocp_vscode import show
    show(build_pcb_phantom(), names=["pcb_phantom"])
