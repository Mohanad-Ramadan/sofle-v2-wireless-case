"""Floor recesses for the battery system: the cell pocket, its JST pocket, and the wire run
between them.

All three are blind recesses cut DOWN from the floor's top face and returned as cutter Parts, so
the tray subtracts them rather than modelling them. They are one system — a cell, the connector
that feeds it, and the leads joining the two — which is why they live together.
"""
from __future__ import annotations
from itertools import pairwise
from typing import cast
from build123d import (
    Axis, BuildPart, BuildSketch, Part, Plane, Pos, Rectangle, Solid, extrude, fillet,
)
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


def jst_body_center(mount: str = "east") -> tuple[float, float]:
    """Case (x, y) centre of the JST body for a given mounting position — NOT its footprint origin.

    Two corrections live here, both of which the model originally got wrong by centring on
    ``JST_POS``:

      * X — ``JST_POS`` is PIN 1. The drill file gives a three-hole row running east at
        ``JST_PIN_PITCH``, and the 2-circuit XH sits on one PAIR of the three holes;
      * Y — the part is SIDE ENTRY. Its pins leave the back of the shroud, so the body does not
        straddle the pin row; it runs off it, northward, in the same direction the plug enters.

    ``mount`` is "east" or "west". Both are electrically valid — the middle hole is B+ and both
    outer holes are GND — so this is a real choice the owner keeps, not a detail to be frozen by
    whichever one got soldered first. The pocket is cut to the union of the two.
    """
    index = {"east": C.JST_MOUNT_E, "west": C.JST_MOUNT_W}[mount]
    cx = C.pcb_to_case(C.JST_POS[0] + index * C.JST_PIN_PITCH, C.JST_POS[1])[0]
    pin_row_y = C.pcb_to_case(*C.JST_POS)[1]
    return cx, pin_row_y + C.JST_BODY_D / 2


def _slide_switch_south_y() -> float:
    """Case Y of the slide switch phantom's south face — the JST pocket's south edge lines up
    with it, by the owner's eye.

    Derived live rather than frozen as a literal. A copied number here is precisely the bug this
    project keeps hitting: ``switch_phantom._LOWER_H`` sat as a stale copy of ``MX_BODY_CLEAR``
    through two revisions of the value it claimed to be. The cost is that a structural cutter now
    reads a phantom module, which is normally the wrong direction — but the alignment target IS
    the phantom's face, so deriving anything else would be describing a different edge.
    """
    from .pcb_phantom import _slide_switch_body
    return _slide_switch_body().bounding_box().min.Y


def _jst_pocket_bounds() -> tuple[float, float, float, float]:
    """(x_lo, x_hi, y_lo, y_hi) of the JST pocket in case coords.

    Shared with the wire channel so the two recesses cannot drift apart and leave the leads
    crossing solid floor.

    In X it spans the UNION of both mounting positions, so the connector can sit on either pair of
    holes without a reprint — see ``jst_body_center``. That costs one pin pitch of width (11.54
    against 9.00) and keeps a choice the board's wiring genuinely leaves open.

    The south edge is the slide switch's south face; that lands 0.84 mm south of the pin row,
    which is margin the pin tails want anyway. North of the body it runs on to swallow the mated
    plug (``JST_PLUG_RUN``) and the bend past it (``JST_WIRE_BEND``).
    """
    west_x, by = jst_body_center("west")
    east_x, _ = jst_body_center("east")
    half_w = C.JST_BODY_W / 2 + C.JST_POCKET_PAD
    y_lo = _slide_switch_south_y()
    y_hi = by + C.JST_BODY_D / 2 + C.JST_PLUG_RUN + C.JST_WIRE_BEND + C.JST_POCKET_PAD
    return west_x - half_w, east_x + half_w, y_lo, y_hi


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


def jst_channel_path() -> list[tuple[float, float]]:
    """Waypoints of the wire route, JST pocket -> battery pocket, in case coords.

    A hooked orthogonal route, not the shortest line: NORTH out of the JST pocket, EAST along the
    top, a long leg SOUTH, then EAST into the battery pocket near its south-west corner. Published
    as points rather than hidden inside the cutter so the clearance tests can walk the real path —
    a diagonal's bounding box lies about where it goes, and so does a hook's.

    The first point sits INSIDE the JST pocket and the last INSIDE the battery pocket, so the
    route is anchored to the recesses it joins rather than merely aimed at them.
    """
    bat = battery_pocket().bounding_box()
    x_lo, x_hi, _, y_hi = _jst_pocket_bounds()
    riser_x = (x_lo + x_hi) / 2
    y_bot = bat.min.Y + C.JST_CHANNEL_BAT_INSET
    return [
        (riser_x, y_hi - _CHANNEL_OVERLAP),          # inside the JST pocket
        (riser_x, C.JST_CHANNEL_TOP_Y),              # north
        (C.JST_CHANNEL_MID_X, C.JST_CHANNEL_TOP_Y),  # east along the top
        (C.JST_CHANNEL_MID_X, y_bot),                # the long leg south
        (bat.min.X + _CHANNEL_OVERLAP, y_bot),       # east, inside the battery pocket
    ]


def jst_wire_channel() -> Part:
    """Cutter part: the run carrying the battery leads from the battery pocket to the JST.

    NOT cosmetic. Only ``STANDOFF_SHOULDER_H`` (2.5 mm) of air exists under the PCB and the
    hotswap sockets eat ~2.0 of it, so a 1.9 mm lead cannot cross the switch field at all
    without this.

    Built as overlapping axis-aligned boxes along ``jst_channel_path``. Each leg is extended half
    a channel width past both ends, which is what fills the corners — butt-jointed legs would
    leave a notch on the outside of every turn, exactly where a lead is pressed hardest.

    Cut to ``JST_CHANNEL_FLOOR_Z``, which is the JST pocket's floor, not a wire-sized depth — see
    the constants note.
    """
    z_lo, z_hi = C.JST_CHANNEL_FLOOR_Z, C.FLOOR_THICKNESS
    half = C.JST_CHANNEL_W / 2
    pts = jst_channel_path()

    legs = []
    for (x0, y0), (x1, y1) in pairwise(pts):
        if abs(y1 - y0) < 1e-9:                      # horizontal leg
            lo, hi = min(x0, x1) - half, max(x0, x1) + half
            cx, cy, dx, dy = (lo + hi) / 2, y0, hi - lo, C.JST_CHANNEL_W
        else:                                        # vertical leg
            lo, hi = min(y0, y1) - half, max(y0, y1) + half
            cx, cy, dx, dy = x0, (lo + hi) / 2, C.JST_CHANNEL_W, hi - lo
        legs.append(Solid.make_box(dx, dy, z_hi - z_lo).translate((cx - dx / 2, cy - dy / 2, z_lo)))

    run = legs[0]
    for leg in legs[1:]:
        run = cast(Part, run + leg)
    return cast(Part, run)


# %%
if __name__ == "__main__":
    # battery_pocket et al are defined right here — no self-import needed
    from ocp_vscode import show
    show(battery_pocket(), jst_pocket(), jst_wire_channel(),
         names=["battery", "jst", "wire channel"])
