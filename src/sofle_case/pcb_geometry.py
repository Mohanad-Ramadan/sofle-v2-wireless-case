"""Load cached PCB outline polygon and translate into case coords."""
from __future__ import annotations
import json
from pathlib import Path
from . import constants as C


_DATA = Path(__file__).resolve().parents[2] / "data"


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
