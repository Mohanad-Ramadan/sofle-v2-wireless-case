"""MX switch phantom for visual fit-check in the OCP viewer. Gate with SHOW_SWITCH_PHANTOM."""
from __future__ import annotations
import json
from pathlib import Path

from build123d import (
    Part, BuildPart, Locations, Location, Box, Cylinder,
)
from . import constants as C

_DATA = Path(__file__).resolve().parents[2] / "data"

# Cherry MX geometry — phantom only, not structural
_LOWER_W  = 13.8   # lower housing width/depth (fits through 14×14 plate cutout)
_LOWER_H  =  3.0   # lower housing height = measured MX body clearance gap
_UPPER_W  = 15.6   # upper housing width/depth
_UPPER_H  =  6.6   # upper housing height above plate
_STEM_DIA =  4.5   # stem cylinder diameter
_STEM_H   =  3.5   # stem cylinder height above upper housing


def _load_switch_positions() -> list[dict]:
    """Return top-layer MX switch entries from components.json (excludes encoder SW25)."""
    raw = json.loads((_DATA / "components.json").read_text())
    return [
        {"name": k, "x": v["x"], "y": v["y"], "rot": v["rotation"]}
        for k, v in raw.items()
        if k.startswith("SW") and v.get("layer") == "top" and k != "SW25"
    ]


def _mx_switch_solid(cx: float, cy: float, rot: float) -> Part:
    """Three-part MX switch: lower housing + upper housing + stem."""
    lower_z = C.PLATE_SEAT_Z - _LOWER_H / 2
    upper_z = C.PLATE_TOP_Z  + _UPPER_H / 2
    stem_z  = C.PLATE_TOP_Z  + _UPPER_H + _STEM_H / 2

    with BuildPart() as bp:
        with Locations(Location((cx, cy, lower_z), (0, 0, rot))):
            Box(_LOWER_W, _LOWER_W, _LOWER_H)
        with Locations(Location((cx, cy, upper_z), (0, 0, rot))):
            Box(_UPPER_W, _UPPER_W, _UPPER_H)
        with Locations((cx, cy, stem_z)):
            Cylinder(radius=_STEM_DIA / 2, height=_STEM_H)

    assert bp.part is not None
    return bp.part


def build_switch_phantom() -> Part:
    """All 29 MX switches as a single Part compound."""
    children: list[Part] = []
    for sw in _load_switch_positions():
        cx, cy = C.pcb_to_case(sw["x"], sw["y"])
        children.append(_mx_switch_solid(cx, cy, sw["rot"]))
    return Part(children=children)


if __name__ == "__main__":
    from ocp_vscode import show
    show(build_switch_phantom(), name="switch_phantom")
