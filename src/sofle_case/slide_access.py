"""Shared outer-side finger access, authored in registered right-half coordinates."""
from __future__ import annotations

from typing import cast

from build123d import (
    Box,
    BuildSketch,
    Location,
    Locations,
    Part,
    Plane,
    Pos,
    RectangleRounded,
    Solid,
)
from OCP.Approx import Approx_IsoParametric
from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections

from . import constants as C
from .pcb_geometry import slide_switch_placement


def slide_finger_cutout() -> Part:
    """One continuous concave port; no flat back-wall ledge or nested slot."""
    cx, cy, rotation = slide_switch_placement()
    front = -(C.SLIDE_ACTUATOR_BODY_W / 2 + C.SLIDE_ACTUATOR_NUB_D)
    outer = front - C.SLIDE_ACCESS_OUTER_REACH
    clear = C.SLIDE_ACCESS_CLEARANCE
    rear_w = C.SLIDE_ACTUATOR_NUB_L + 2 * clear
    rear_h = C.SLIDE_ACTUATOR_NUB_H + 2 * clear
    stations = []
    for t in (0.0, 0.25, 0.5, 0.75, 1.0):
        blend = t * t * (3 - 2 * t)
        stations.append((
            t * C.SLIDE_ACCESS_OUTER_REACH,
            C.SLIDE_ACCESS_W + blend * (C.SLIDE_ACCESS_CONTROL_W - C.SLIDE_ACCESS_W),
            C.SLIDE_ACCESS_H + blend * (C.SLIDE_ACCESS_CONTROL_H - C.SLIDE_ACCESS_H),
            C.SLIDE_ACCESS_CENTER_Z, C.SLIDE_ACCESS_RADIUS,
        ))
    # The tighter return starts behind the contact face, not in the approach.
    for t in (0.25, 0.5, 0.75, 1.0):
        blend = t * t * (3 - 2 * t)
        stations.append((
            C.SLIDE_ACCESS_OUTER_REACH + t * C.SLIDE_ACCESS_REAR_BLEND_D,
            C.SLIDE_ACCESS_CONTROL_W + blend * (rear_w - C.SLIDE_ACCESS_CONTROL_W),
            C.SLIDE_ACCESS_CONTROL_H + blend * (rear_h - C.SLIDE_ACCESS_CONTROL_H),
            C.SLIDE_ACCESS_CENTER_Z + blend * (C.SLIDE_NUB_Z - C.SLIDE_ACCESS_CENTER_Z),
            C.SLIDE_ACCESS_RADIUS + blend * (clear - C.SLIDE_ACCESS_RADIUS),
        ))
    stations.append((
        C.SLIDE_ACCESS_OUTER_REACH + C.SLIDE_ACTUATOR_NUB_D + clear,
        rear_w, rear_h, C.SLIDE_NUB_Z, clear,
    ))
    cutter = BRepOffsetAPI_ThruSections(True, False)
    cutter.SetMaxDegree(3)
    cutter.SetParType(Approx_IsoParametric)
    for depth, width, height, z, radius in stations:
        with BuildSketch(Plane.XZ.offset(-(outer + depth))) as profile, Locations(
            (C.SLIDE_ACTUATOR_PIN_CENTER_X, z)
        ):
            RectangleRounded(width, height, radius)
        cutter.AddWire(profile.sketch.face().outer_wire().wrapped)
    cutter.Build()
    return cast(Part, Location((cx, cy, 0), (0, 0, rotation)) *
                Part([Solid(cutter.Shape())]))


def slide_body_cavity(top_z: float) -> Part:
    """Internal can clearance; the concave port supplies actuator clearance."""
    cx, cy, rotation = slide_switch_placement()
    z0 = C.PCB_TOP_Z - 0.3
    pad = C.SLIDE_ACTUATOR_PAD
    body = Pos(C.SLIDE_ACTUATOR_PIN_CENTER_X, 0, (z0 + top_z) / 2) * Box(
        C.SLIDE_ACTUATOR_BODY_L + 2 * pad,
        C.SLIDE_ACTUATOR_BODY_W + 2 * pad,
        top_z - z0,
    )
    return cast(Part, Location((cx, cy, 0), (0, 0, rotation)) * body)


if __name__ == "__main__":
    from ocp_vscode import show

    show(slide_finger_cutout())
