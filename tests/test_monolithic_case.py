"""Regression tests for the surface-less monolithic case."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from build123d import (
    BuildLine,
    Kind,
    Part,
    Plane,
    Polyline,
    Pos,
    Solid,
    extrude,
    make_face,
    mirror,
    offset,
)

from sofle_case import constants as C
from sofle_case.pcb_phantom import (
    _jst_body,
    _mcu_block,
    _slide_switch_body,
    build_pcb_phantom,
)
from sofle_case.switch_phantom import build_switch_phantom
from tests.shared_builds import build_case_half

_DATA = Path(__file__).resolve().parents[1] / "data"


def _load_raw_plate_polygon() -> list[tuple[float, float]]:
    """Read the authoritative plate points without importing plate geometry helpers."""
    raw = json.loads((_DATA / "plate_outline.json").read_text())
    points = [tuple(point) for point in raw]
    if points and points[0] == points[-1]:
        points.pop()
    return points  # type: ignore[return-value]


def _raw_plate_fit_cutter(
    z_lo: float = C.PLATE_SEAT_Z,
    z_hi: float = C.PLATE_TOP_Z,
    xy_growth: float = 0.0,
    side: str = "right",
) -> Part:
    """Build a fit probe from the raw JSON outline, independently of production points."""
    case_points = [C.pcb_to_case(x, y) for x, y in _load_raw_plate_polygon()]
    if side == "left":
        case_points = [(C.OUTER_WIDTH - x, y) for x, y in case_points]
    with BuildLine() as bl:
        Polyline(*case_points, close=True)
    face = make_face(bl.line)
    if xy_growth:
        face = offset(face, amount=xy_growth, kind=Kind.INTERSECTION)
    return Pos(0, 0, z_lo) * extrude(face, amount=z_hi - z_lo)


def _raw_plate_edge_probe(
    edge_index: int,
    z_lo: float,
    z_hi: float,
    side: str,
    *,
    edge_margin: float = 0.2,
    wall_depth: float = 0.15,
) -> Part:
    """Return a thin outboard strip beside one raw plate-outline edge.

    The strip is intentionally made from the JSON contour rather than from a
    plate/case helper.  It avoids the endpoints so a corner fillet cannot hide
    a discontinuity in the wall along the edge proper.
    """
    points = [C.pcb_to_case(x, y) for x, y in _load_raw_plate_polygon()]
    if side == "left":
        points = [(C.OUTER_WIDTH - x, y) for x, y in points]
    start = points[edge_index]
    end = points[(edge_index + 1) % len(points)]
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = (dx * dx + dy * dy) ** 0.5
    assert length > 2 * edge_margin
    tx, ty = dx / length, dy / length

    # The transformed contour is clockwise for the right case and
    # counter-clockwise after mirroring, so use its signed area to select the
    # normal that points away from the plate footprint.
    signed_area = sum(
        x0 * y1 - x1 * y0
        for (x0, y0), (x1, y1) in zip(points, points[1:] + points[:1])
    )
    out_x, out_y = (ty, -tx) if signed_area > 0 else (-ty, tx)
    a = (start[0] + edge_margin * tx, start[1] + edge_margin * ty)
    b = (end[0] - edge_margin * tx, end[1] - edge_margin * ty)
    strip = [
        a,
        b,
        (b[0] + wall_depth * out_x, b[1] + wall_depth * out_y),
        (a[0] + wall_depth * out_x, a[1] + wall_depth * out_y),
    ]
    with BuildLine() as bl:
        Polyline(*strip, close=True)
    return Pos(0, 0, z_lo) * extrude(make_face(bl.line), amount=z_hi - z_lo)


def _authoritative_mcu_notch_cutter(
    z_lo: float, z_hi: float, side: str = "right"
) -> Part:
    """Build an independent probe from the raw plate outline.

    This intentionally does not call the production notch helper: the final
    case tests must be able to catch a helper that returns the wrong region.
    """
    points = _load_raw_plate_polygon()
    edges = [
        (p0, p1) for p0, p1 in zip(points, points[1:] + points[:1])
        if abs(p1[0] - p0[0]) <= 0.1 and abs(p1[1] - p0[1]) > 40.0
    ]
    east_lo, east_hi = min(edges, key=lambda e: min(e[0][0], e[1][0]))
    if east_lo[1] > east_hi[1]:
        east_lo, east_hi = east_hi, east_lo
    west_lo = max(
        (p for p in points if p[0] < east_lo[0] and abs(p[1] - east_lo[1]) <= 0.1),
        key=lambda p: p[0],
    )
    notch_pcb = [
        west_lo,
        (west_lo[0], east_hi[1]),
        east_hi,
        east_lo,
    ]
    notch_case = [C.pcb_to_case(x, y) for x, y in notch_pcb]
    if side == "left":
        notch_case = [(C.OUTER_WIDTH - x, y) for x, y in notch_case]
    with BuildLine() as bl:
        Polyline(*notch_case, close=True)
    return Pos(0, 0, z_lo) * extrude(
        make_face(bl.line), amount=z_hi - z_lo
    )


def test_case_half_is_one_flush_solid():
    right = build_case_half("right")
    left = build_case_half("left")
    for part in (right, left):
        assert isinstance(part, Part)
        assert len(part.solids()) == 1
        assert abs(part.bounding_box().max.Z - C.PLATE_TOP_Z) < 0.01
    assert abs(left.volume - right.volume) < 1e-6
    assert abs(left.bounding_box().min.X - (C.OUTER_WIDTH - right.bounding_box().max.X)) < 1e-6
    assert abs(left.bounding_box().max.X - (C.OUTER_WIDTH - right.bounding_box().min.X)) < 1e-6


def test_all_five_boss_bores_survive_case_fusion():
    case = build_case_half("right")
    for hole in C.MOUNTING_HOLES:
        x, y = C.pcb_to_case(*hole)
        bore = Solid.make_cylinder(
            C.STANDOFF_TAP_DIA / 2 - 0.05,
            C.STANDOFF_BORE_DEPTH - 0.2,
        ).translate((x, y, C.PLATE_SEAT_Z - C.STANDOFF_BORE_DEPTH + 0.1))
        boss = Solid.make_cylinder(C.STANDOFF_OD_UPPER / 2 - 0.1, 0.2).translate(
            (x, y, C.PCB_TOP_Z + 0.5)
        )
        assert (case & bore).volume < 0.1 * bore.volume
        assert (case & boss).volume > 0.5 * boss.volume


def test_case_api_has_no_clamshell_builders():
    from sofle_case import case

    assert not hasattr(case, "build_top_part")
    assert not hasattr(case, "build_bottom_part")


def test_plate_fit_is_nominally_clear_and_bay_stays_open():
    for side in ("right", "left"):
        case = build_case_half(side)
        plate = _raw_plate_fit_cutter(side=side)
        assert (case & plate).volume < 1e-3
        assert (case & _raw_plate_fit_cutter(xy_growth=0.01, side=side)).volume > 0.0

        mcu_block = _mcu_block()
        if side == "left":
            mcu_block = _mirror_left(mcu_block)
        assert (case & mcu_block).volume < 1e-3


@pytest.mark.parametrize("side", ["right", "left"])
def test_plate_fit_band_tracks_raw_outline_without_local_wall_gaps(side: str):
    """The fit-band wall stays continuous along straight, concave, and notch edges."""
    case = build_case_half(side)

    # These raw-contour segments respectively cover the long east run, the
    # upper concave step, and the straight edge immediately beside the MCU
    # notch.  A shifted or enlarged plate cutter leaves one of their outboard
    # strips empty; a shrunken cutter instead fails the raw-footprint probe.
    representative_edges = (9, 2, 0)
    for z in (C.PLATE_SEAT_Z + 0.01,
              (C.PLATE_SEAT_Z + C.PLATE_TOP_Z) / 2,
              C.PLATE_TOP_Z - 0.02):
        plate_slice = _raw_plate_fit_cutter(z, z + 0.01, side=side)
        assert (case & plate_slice).volume < 1e-3
        for edge_index in representative_edges:
            wall = _raw_plate_edge_probe(edge_index, z, z + 0.01, side)
            assert (case & wall).volume > 0.95 * wall.volume


@pytest.mark.parametrize("side", ["right", "left"])
def test_complete_authoritative_mcu_notch_is_open_at_each_fit_band_height(side: str):
    case = build_case_half(side)
    for z in (C.PLATE_SEAT_Z, (C.PLATE_SEAT_Z + C.PLATE_TOP_Z) / 2,
              C.PLATE_TOP_Z - 0.01):
        notch = _authoritative_mcu_notch_cutter(z, z + 0.01, side)
        assert (case & notch).volume < 1e-3


def test_mcu_notch_opening_does_not_cut_below_plate_seat():
    case = build_case_half("right")
    below_notch = _authoritative_mcu_notch_cutter(
        C.PLATE_SEAT_Z - 1.0, C.PLATE_SEAT_Z
    )
    assert (case & below_notch).volume < 1e-3
    # The adjacent lower west wall remains present, guarding against a broad
    # through-bottom notch cutter rather than a fit-band-only subtraction.
    wall_probe = Solid.make_box(0.1, 0.1, 0.1).translate(
        (13.0, 80.0, C.PLATE_SEAT_Z - 0.1)
    )
    assert (case & wall_probe).volume > 0.0


def test_final_case_clears_rotated_slide_hardware():
    case = build_case_half("right")
    assert (case & _slide_switch_body()).volume < 1e-3


def _mirror_left(part: Part) -> Part:
    """Place a right-hand phantom on the mirrored left-hand case."""
    return Pos(C.OUTER_WIDTH / 2, 0, 0) * mirror(
        Pos(-C.OUTER_WIDTH / 2, 0, 0) * part,
        about=Plane.YZ,
    )


@pytest.mark.parametrize("side", ["right", "left"])
def test_final_case_clears_complete_pcb_and_switch_hardware(side: str):
    """The assembled hardware envelope must not intersect either printable half."""
    case = build_case_half(side)
    pcb = build_pcb_phantom(side)
    switches = build_switch_phantom()
    if side == "left":
        pcb = _mirror_left(pcb)
        switches = _mirror_left(switches)

    assert (case & pcb).volume < 1e-3
    assert (case & switches).volume < 1e-3

    # The pocket supports either legal JST mounting-hole pair; check the alternate
    # west position too, rather than proving only the default east position fits.
    jst = _jst_body(mount="west")
    if side == "left":
        jst = _mirror_left(jst)
    assert (case & jst).volume < 1e-3


def test_structural_build_does_not_import_phantom_module():
    code = ("import sys; from sofle_case.case import build_case_half; "
            "build_case_half('right'); "
            "assert 'sofle_case.pcb_phantom' not in sys.modules")
    subprocess.run([sys.executable, "-c", code], check=True)
