"""Authoritative switch-plate plan geometry shared by structure and phantoms."""
from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from build123d import (
    BuildLine,
    Kind,
    Part,
    Polyline,
    Pos,
    Wire,
    extrude,
    make_face,
    offset,
)

from . import constants as C

_DATA = Path(__file__).resolve().parents[2] / "data"


def load_plate_polygon() -> list[tuple[float, float]]:
    raw = json.loads((_DATA / "plate_outline.json").read_text())
    return [tuple(p) for p in raw]  # type: ignore[return-value]


def load_plate_cutouts() -> list[list[tuple[float, float]]]:
    raw = json.loads((_DATA / "plate_cutouts.json").read_text())
    return [[tuple(p) for p in cut] for cut in raw]  # type: ignore[return-value]


def plate_case_points() -> list[tuple[float, float]]:
    return [C.pcb_to_case(x, y) for x, y in load_plate_polygon()]


def plate_wire() -> Wire:
    points = plate_case_points()
    if points and points[0] == points[-1]:
        points = points[:-1]
    with BuildLine() as bl:
        Polyline(*points, close=True)
    return cast(Wire, bl.line)


def plate_mcu_notch_polygon() -> list[tuple[float, float]]:
    """Return the complete west MCU notch in case coordinates.

    The plate gerber describes this opening as the long, very slightly sloped
    edge between the two west-side jogs.  Its other edge is the short segment
    of the same outline at the lower end of that edge; extending that segment
    to the upper endpoint gives the notch's authoritative quadrilateral.  In
    particular, this is deliberately *not* reconstructed from the nice!nano
    component envelope: the plate outline is the source of truth, including
    the approximately 0.004 mm east-edge slope.
    """
    points = load_plate_polygon()
    if points and points[0] == points[-1]:
        points = points[:-1]

    # Find the long west-side edge (the MCU opening) rather than encoding its
    # dimensions or point indices.  The outer east edge is also long, so the
    # westmost long edge unambiguously selects the notch boundary.
    edges = []
    for index, (p0, p1) in enumerate(zip(points, points[1:] + points[:1])):
        dx = p1[0] - p0[0]
        dy = p1[1] - p0[1]
        if abs(dx) <= 0.1 and abs(dy) > 40.0:
            edges.append((p0, p1, index))
    if not edges:
        raise ValueError("plate outline has no long MCU-notch edge")
    east_lo, east_hi, _ = min(edges, key=lambda edge: min(edge[0][0], edge[1][0]))
    if east_lo[1] > east_hi[1]:
        east_lo, east_hi = east_hi, east_lo

    # The lower endpoint has an adjacent west-side outline point at the same
    # Y.  Derive the west boundary from that point, then close the notch at the
    # upper endpoint of the sloped edge.
    west_candidates = [
        p for p in points
        if p[0] < east_lo[0] and abs(p[1] - east_lo[1]) <= 0.1
    ]
    if not west_candidates:
        raise ValueError("plate outline has no west MCU-notch boundary")
    west_lo = max(west_candidates, key=lambda p: p[0])
    notch_pcb = [
        west_lo,
        (west_lo[0], east_hi[1]),
        east_hi,
        east_lo,
    ]
    return [C.pcb_to_case(x, y) for x, y in notch_pcb]


def mcu_notch_polygon() -> list[tuple[float, float]]:
    """Alias for :func:`plate_mcu_notch_polygon` used by fit consumers."""
    return plate_mcu_notch_polygon()


def _polygon_face(points: list[tuple[float, float]]):
    with BuildLine() as bl:
        Polyline(*points, close=True)
    return make_face(cast(Wire, bl.line))


def mcu_notch_cutter(z_lo: float = C.PLATE_SEAT_Z,
                     z_hi: float = C.PLATE_TOP_Z,
                     xy_clearance: float = 0.0) -> Part:
    """Solid for the complete authoritative MCU notch over a Z interval."""
    face = _polygon_face(plate_mcu_notch_polygon())
    if xy_clearance:
        face = offset(face, amount=xy_clearance, kind=Kind.INTERSECTION)
    return cast(Part, Pos(0, 0, z_lo) * extrude(face, amount=z_hi - z_lo))


def plate_mcu_notch_cutter(z_lo: float = C.PLATE_SEAT_Z,
                           z_hi: float = C.PLATE_TOP_Z,
                           xy_clearance: float = 0.0) -> Part:
    """Explicit plate-prefixed alias for :func:`mcu_notch_cutter`."""
    return mcu_notch_cutter(z_lo=z_lo, z_hi=z_hi, xy_clearance=xy_clearance)


def plate_fit_cutter(z_lo: float = C.PLATE_SEAT_Z,
                     z_hi: float = C.PLATE_TOP_Z,
                     xy_clearance: float = 0.0) -> Part:
    """Plate envelope; nominal geometry has zero XY clearance and no lead-in."""
    face = make_face(plate_wire())
    if xy_clearance:
        face = offset(face, amount=xy_clearance, kind=Kind.INTERSECTION)
    return cast(Part, Pos(0, 0, z_lo) * extrude(face, amount=z_hi - z_lo))
