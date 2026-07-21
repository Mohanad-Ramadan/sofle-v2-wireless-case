"""Load cached PCB outline polygon and translate into case coords."""
from __future__ import annotations
import json
import math
from pathlib import Path
from . import constants as C


_DATA = Path(__file__).resolve().parents[2] / "data"


def rotate_2d(lx: float, ly: float, deg: float) -> tuple[float, float]:
    """Rotate a local (x, y) offset by *deg* degrees CCW."""
    r = math.radians(deg)
    return lx * math.cos(r) - ly * math.sin(r), lx * math.sin(r) + ly * math.cos(r)


def slide_switch_placement() -> tuple[float, float, float]:
    """SK12D07VG3 (SW31) footprint origin in case coords + rotation (degrees).

    Reads components.json and maps through pcb_to_case, so both the phantom body
    and the structural actuator cavity register off the SAME placement — the cavity
    tracks the switch exactly instead of hard-coding case coordinates."""
    raw = json.loads((_DATA / "components.json").read_text())
    sw = raw["SW31"]
    cx, cy = C.pcb_to_case(sw["x"], sw["y"])
    return cx, cy, sw["rotation"]


def load_pcb_polygon() -> list[tuple[float, float]]:
    """Ordered closed polygon in PCB coords (first == last)."""
    raw = json.loads((_DATA / "pcb_outline.json").read_text())
    return [tuple(p) for p in raw]


def load_mounting_holes() -> list[tuple[float, float]]:
    raw = json.loads((_DATA / "mounting_holes.json").read_text())
    return [tuple(p) for p in raw]


def polygon_in_case_coords() -> list[tuple[float, float]]:
    return [C.pcb_to_case(x, y) for x, y in load_pcb_polygon()]


def holes_in_case_coords() -> list[tuple[float, float]]:
    return [C.pcb_to_case(x, y) for x, y in load_mounting_holes()]
