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
_LOWER_H  =  C.MX_BODY_CLEAR   # lower housing height = plate-to-PCB gap the switch body sits in.
                                # Was a stale literal 3.0, a copy of the pre-fix MX_BODY_CLEAR;
                                # tracked the wrong thing and drifted when that value moved to 3.40.
_UPPER_W  = 15.6   # upper housing width/depth
_UPPER_H  =  6.6   # upper housing height above plate
_STEM_DIA =  4.5   # stem cylinder diameter
_STEM_H   =  3.5   # stem cylinder height above upper housing

# Keycap — APPROXIMATE, and only ever used to answer "how tall does this thing read next to the
# keys". A Cherry/OEM-profile cap swallows most of the stem: its underside sits ~1.0 mm above the
# upper housing and the cap body is ~9.4 mm tall, sloping from an 18 mm base to a ~14 mm top. That
# puts the crown ~17 mm above the plate. Not a fit-check part — nothing may depend on it.
_CAP_BASE_W   = 18.0
_CAP_TOP_W    = 14.0
_CAP_H        =  9.4
_CAP_GAP      =  1.0   # cap underside above the upper housing


def _load_switch_positions() -> list[dict]:
    """Return top-layer MX switch entries from components.json (excludes encoder SW25)."""
    raw = json.loads((_DATA / "components.json").read_text())
    return [
        {"name": k, "x": v["x"], "y": v["y"], "rot": v["rotation"]}
        for k, v in raw.items()
        if k.startswith("SW") and v.get("layer") == "top" and k != "SW25"
    ]


def _keycap_solid(cx: float, cy: float) -> Part:
    """One approximate keycap: a truncated pyramid on top of the switch. See the _CAP_* note.

    No ``rot``, unlike the switch below: the cap is square about its own axis, so rotating it is a
    no-op — and taking the argument would imply the caps are oriented when they are not."""
    base_z = C.PLATE_TOP_Z + _UPPER_H + _CAP_GAP
    # taper by lofting base → top square
    from build123d import loft, BuildSketch, Rectangle, Location
    with BuildSketch() as lo:
        Rectangle(_CAP_BASE_W, _CAP_BASE_W)
    with BuildSketch() as hi:
        Rectangle(_CAP_TOP_W, _CAP_TOP_W)
    f_lo = lo.sketch.faces()[0].moved(Location((cx, cy, base_z)))
    f_hi = hi.sketch.faces()[0].moved(Location((cx, cy, base_z + _CAP_H)))
    return loft([f_lo, f_hi])


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


def build_switch_phantom(with_keycaps: bool = False) -> Part:
    """All 29 MX switches as a single Part compound.

    ``with_keycaps`` adds approximate caps — the only honest way to judge whether something like
    the encoder knob reads tall, since the switches alone stop 5 mm below the surface your fingers
    actually touch."""
    children: list[Part] = []
    for sw in _load_switch_positions():
        cx, cy = C.pcb_to_case(sw["x"], sw["y"])
        children.append(_mx_switch_solid(cx, cy, sw["rot"]))
        if with_keycaps:
            children.append(_keycap_solid(cx, cy))
    return Part(children=children)


def keycap_top_z() -> float:
    """Approximate Z of a keycap crown — the datum the knob's height should be judged against."""
    return C.PLATE_TOP_Z + _UPPER_H + _CAP_GAP + _CAP_H


if __name__ == "__main__":
    from ocp_vscode import show
    show(build_switch_phantom(), names=["switch_phantom"])
