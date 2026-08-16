"""Floor recesses for the battery system: the cell pocket, its JST pocket, and the wire run
between them.

All three are blind recesses cut DOWN from the floor's top face and returned as cutter Parts, so
the tray subtracts them rather than modelling them. They are one system — a cell, the connector
that feeds it, and the leads joining the two — which is why they live together.
"""
from __future__ import annotations
from typing import cast
from build123d import Part, BuildPart, BuildSketch, Plane, Pos, Rectangle, extrude, fillet, Axis
from . import constants as C

# Both ends of the wire channel reach INTO the pockets they join. A channel that merely abutted
# them would meet at a zero-width face, which OCC is entitled to treat as a non-intersection —
# the leads would then be asked to cross a wall that the render shows as open.
_CHANNEL_OVERLAP = 1.0  # mm


def battery_pocket() -> Part:
    """Cutter part: subtract from the tray to recess the battery pocket into the floor.

    Spans Z = (FLOOR_THICKNESS − BATTERY_POCKET_DEPTH) → FLOOR_THICKNESS, a blind recess
    cut down from the floor's top face, leaving BATTERY_FLOOR_BASE of solid floor beneath.
    The center is shifted +BATTERY_POCKET_SHIFT_X (east) so the enlarged footprint grows
    into the roomy east/north/south space while the two west standoffs stay clear.
    """
    cx, cy = C.pcb_to_case(C.BATTERY_POCKET_POS[0] + C.BATTERY_POCKET_SHIFT_X,
                           C.BATTERY_POCKET_POS[1])
    half_w = C.BATTERY_W / 2 + C.BATTERY_XY_CLEARANCE
    half_l = C.BATTERY_L / 2 + C.BATTERY_XY_CLEARANCE
    z_lo = C.FLOOR_THICKNESS - C.BATTERY_POCKET_DEPTH
    z_hi = C.FLOOR_THICKNESS

    with BuildPart() as bp:
        with BuildSketch(Plane.XY.offset(z_lo)):
            Rectangle(half_w * 2, half_l * 2)
        extrude(amount=z_hi - z_lo)
        vertical = bp.edges().filter_by(Axis.Z)
        if vertical:
            fillet(vertical, radius=C.BATTERY_POCKET_CORNER_R)
    assert bp.part is not None
    return cast(Part, Pos(cx, cy, 0) * bp.part)


def _jst_pocket_bounds() -> tuple[float, float, float, float]:
    """(x_lo, x_hi, y_lo, y_hi) of the JST pocket in case coords.

    Shared with the wire channel so the two recesses cannot drift apart and leave the leads
    crossing solid floor. The pocket is NOT centred on J2: it runs north of the footprint to
    swallow the mated plug (``JST_PLUG_RUN``) and the bend past it (``JST_WIRE_BEND``).
    """
    cx, cy = C.pcb_to_case(*C.JST_POS)
    half_w = C.JST_BODY_W / 2 + C.JST_POCKET_PAD
    y_lo = cy - (C.JST_BODY_D / 2 + C.JST_POCKET_PAD)
    y_hi = cy + (C.JST_BODY_D / 2 + C.JST_PLUG_RUN + C.JST_WIRE_BEND + C.JST_POCKET_PAD)
    return cx - half_w, cx + half_w, y_lo, y_hi


def jst_pocket() -> Part:
    """Cutter part: blind recess in the floor for the battery JST hung UNDER the PCB.

    The connector used to stand on top of the board, where it fouled the cover by 34.2 mm^3 and
    held the case open — the only piece of hardware that did. Mounting it underneath, like the
    hotswap sockets, removes the collision instead of reshaping the canopy around it.

    Spans ``JST_POCKET_FLOOR_Z`` -> ``FLOOR_THICKNESS``, cut down from the floor's top face
    exactly as ``battery_pocket`` is. It looks alarmingly deep against the 6.3 mm nominal floor
    — the floor is only 0.70 mm below it — but the tent wedge carries roughly 14.5 mm of material
    here, leaving ~8.9 mm beneath. That margin is the wedge's, NOT the floor's, so it is asserted
    by probing the built part rather than trusted from these constants.
    """
    x_lo, x_hi, y_lo, y_hi = _jst_pocket_bounds()
    z_lo, z_hi = C.JST_POCKET_FLOOR_Z, C.FLOOR_THICKNESS

    with BuildPart() as bp:
        with BuildSketch(Plane.XY.offset(z_lo)):
            Rectangle(x_hi - x_lo, y_hi - y_lo)
        extrude(amount=z_hi - z_lo)
        vertical = bp.edges().filter_by(Axis.Z)
        if vertical:
            fillet(vertical, radius=C.JST_POCKET_CORNER_R)
    assert bp.part is not None
    return cast(Part, Pos((x_lo + x_hi) / 2, (y_lo + y_hi) / 2, 0) * bp.part)


def jst_wire_channel() -> Part:
    """Cutter part: the shallow run carrying the battery leads from the JST pocket east.

    NOT cosmetic. Only ``STANDOFF_SHOULDER_H`` (2.5 mm) of air exists under the PCB and the
    hotswap sockets eat ~2.0 of it, so a 1.9 mm lead cannot cross the switch field at all without
    this. It is cut only ``JST_CHANNEL_DEPTH`` deep — sized for wire, not for the connector.

    Runs at ``JST_CHANNEL_Y``, which is a clearance decision: routing south of the pocket instead
    would pass 0.46 mm from the standoff at case (53.32, 58.79), while this line clears it by
    ~12 mm. Both ends overlap into the pockets they join so the booleans fuse cleanly instead of
    meeting at a zero-width face.
    """
    _, pocket_x_hi, _, _ = _jst_pocket_bounds()
    bat_x = C.pcb_to_case(C.BATTERY_POCKET_POS[0] + C.BATTERY_POCKET_SHIFT_X,
                          C.BATTERY_POCKET_POS[1])[0]
    x_lo = pocket_x_hi - _CHANNEL_OVERLAP
    x_hi = bat_x - (C.BATTERY_W / 2 + C.BATTERY_XY_CLEARANCE) + _CHANNEL_OVERLAP
    z_lo, z_hi = C.JST_CHANNEL_FLOOR_Z, C.FLOOR_THICKNESS

    with BuildPart() as bp:
        with BuildSketch(Plane.XY.offset(z_lo)):
            Rectangle(x_hi - x_lo, C.JST_CHANNEL_W)
        extrude(amount=z_hi - z_lo)
    assert bp.part is not None
    return cast(Part, Pos((x_lo + x_hi) / 2, C.JST_CHANNEL_Y, 0) * bp.part)


# %%
if __name__ == "__main__":
    from ocp_vscode import show
    from sofle_case.battery import battery_pocket
    show(battery_pocket(), jst_pocket(), jst_wire_channel(),
         names=["battery", "jst", "wire channel"])
