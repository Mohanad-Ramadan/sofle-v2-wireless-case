"""Behaviour tests for the removable MCU/encoder canopy."""
from __future__ import annotations

import json
import math
import struct
from collections import Counter
from pathlib import Path

import pytest
from build123d import (
    Part,
    Solid,
    export_stl,
)

from sofle_case import constants as C
from sofle_case import mcu_encoder_cover as MEC
from sofle_case import tray as Tray
from tests.shared_builds import build_mcu_encoder_cover
from tests.test_clearances import _sided

_cover_outer_polygon = MEC._cover_outer_polygon


@pytest.fixture(scope="module")
def covers() -> dict[str, Part]:
    return {side: build_mcu_encoder_cover(side) for side in ("right", "left")}


def _probe(x: float, y: float, z: float, size: float = 0.3) -> Solid:
    return Solid.make_box(size, size, size).translate((x-size/2, y-size/2, z-size/2))


def test_cover_is_one_valid_solid_with_open_bottom_and_bosses(covers):
    for side, cover in covers.items():
        assert cover.is_valid and len(cover.solids()) == 1
        assert cover.bounding_box().min.Z == pytest.approx(C.PCB_TOP_Z, abs=0.05)
        cx, cy = C.pcb_to_case(*C.MCU_POS)
        if side == "left":
            cx = C.OUTER_WIDTH - cx
        assert (cover & _probe(cx, cy, C.MAIN_RIM_Z - 1.0)).volume < 1e-5
        for bx, by in MEC._th_positions(side):
            assert (cover & _probe(bx + C.COVER_BOSS_OD/2 - 0.15, by,
                                   C.PCB_TOP_Z + 1.0)).volume > 0.005


def test_roof_uses_exact_tangent_smoothstep_and_flat_side_specific_ridge():
    for side in ("right", "left"):
        z0 = MEC._cover_roof_z(C.COVER_RAMP_FOOT_Y, side)
        z1 = MEC._cover_roof_z(C.COVER_RAMP_TOP_Y, side)
        mid_y = (C.COVER_RAMP_FOOT_Y + C.COVER_RAMP_TOP_Y) / 2
        assert MEC._cover_roof_z(mid_y, side) == pytest.approx((z0 + z1)/2, abs=1e-9)
        eps = 1e-4
        assert (MEC._cover_roof_z(C.COVER_RAMP_FOOT_Y + eps, side)-z0)/eps < 1e-3
        assert (z1-MEC._cover_roof_z(C.COVER_RAMP_TOP_Y-eps, side))/eps < 1e-3
        assert MEC._cover_roof_z(C.COVER_RAMP_TOP_Y + 10, side) == pytest.approx(z1)
    assert C.COVER_TOP_THICKNESS == pytest.approx(1.5)
    assert C.cover_ridge_top_z("right") != C.cover_ridge_top_z("left")


def test_faceted_recess_preserves_flat_lip_wall_and_encoder_clearance(covers):
    enc_x, enc_y, _, bbox_h = MEC._encoder_bbox()
    thickness = C.COVER_SOUTH_WALL_THICKNESS
    apex = enc_y-bbox_h/2-C.COVER_ENCODER_CAVITY_CLEAR-thickness
    depth, half_width, flat_half = (C.COVER_RECESS_DEPTH, C.COVER_RECESS_HALF_WIDTH,
                                   C.COVER_RECESS_FLAT_HALF_WIDTH)
    slope = depth/(half_width-flat_half)
    normal_length = math.hypot(slope, 1)
    for side, cover in covers.items():
        def probe(x, y, z, side=side):
            return _probe(x if side == "right" else C.OUTER_WIDTH-x, y, z, 0.05)

        # The entire central lip is flat, not a circular arc under the knob.
        for dx in (-0.8*flat_half, 0.0, 0.8*flat_half):
            assert (cover & probe(enc_x+dx, apex-0.1, C.COVER_FOOT_Z-0.2)).volume < 1e-6
        stations = [(enc_x+dx, apex, 0.0, 1.0)
                    for dx in (-0.8*flat_half, 0.0, 0.8*flat_half)]
        for sign in (-1, 1):
            stations.append((enc_x+sign*(half_width+flat_half)/2, apex-depth/2,
                             sign*slope/normal_length, 1/normal_length))
        for x, y, nx, ny in stations:
            for offset, solid in ((-0.15, False), (0.15, True),
                                  (thickness-0.15, True), (thickness+0.15, False)):
                volume = (cover & probe(x+nx*offset, y+ny*offset, C.MAIN_RIM_Z+0.8)).volume
                assert (volume > 0.00012) if solid else (volume < 1e-6)
        assert (cover & probe(enc_x, enc_y-bbox_h/2-0.25, C.MAIN_RIM_Z+0.8)).volume < 1e-6


def test_reducing_recess_depth_keeps_flat_lip_wall_and_clearance(monkeypatch):
    monkeypatch.setattr(C, "COVER_RECESS_DEPTH", 0.75)
    cover = MEC.build_mcu_encoder_cover("right")
    assert cover.is_valid and len(cover.solids()) == 1
    x, y, _, bbox_h = MEC._encoder_bbox()
    apex = y-bbox_h/2-C.COVER_ENCODER_CAVITY_CLEAR-C.COVER_SOUTH_WALL_THICKNESS
    assert cover.bounding_box().min.Y == pytest.approx(apex-0.75, abs=0.01)
    assert (cover & _probe(x, apex-0.2, C.COVER_FOOT_Z-0.2, 0.1)).volume < 1e-5
    for offset in (0.2, C.COVER_SOUTH_WALL_THICKNESS-0.2):
        assert (cover & _probe(x, apex+offset, C.MAIN_RIM_Z+0.8, 0.1)).volume > 0.0009
    assert (cover & _probe(x, y-bbox_h/2-0.25, C.MAIN_RIM_Z+0.8, 0.1)).volume < 1e-5


def test_bosses_align_to_th1_th2_and_have_blind_pilots(covers):
    right = covers["right"]
    assert C.COVER_BOSS_OD == pytest.approx(5.5)
    assert C.COVER_BOSS_TAP_DIA == pytest.approx(1.8)
    assert C.COVER_BOSS_BORE_DEPTH == pytest.approx(4.0)
    assert C.COVER_BOSS_BORE_CHAMFER == pytest.approx(0.3)
    for x, y in MEC._th_positions("right"):
        assert (right & _probe(x, y, C.PCB_TOP_Z + 0.15)).volume < 1e-5
        assert (right & _probe(x, y, C.PCB_TOP_Z + 3.8)).volume < 1e-5
        assert (right & _probe(x, y, C.PCB_TOP_Z + 4.25)).volume > 0.005


def test_cover_mount_points_are_named_and_match_authoritative_component_data():
    data = json.loads((Path(__file__).parents[1]/"data/components.json").read_text())
    expected = tuple((data[name]["x"], data[name]["y"]) for name in ("TH1", "TH2"))
    assert C.COVER_MOUNT_HOLES_PCB == expected
    assert MEC._th_positions("right") == [C.pcb_to_case(*p) for p in expected]


def test_usb_is_rounded_and_side_registered_with_half_millimetre_clearance(covers):
    assert C.COVER_USB_PORT_W == pytest.approx(C.USB_C_W + 1.0)
    north = max(y for _, y in _cover_outer_polygon())
    mcu_x = C.pcb_to_case(*C.MCU_POS)[0]
    for side, cover in covers.items():
        x = mcu_x if side == "right" else C.OUTER_WIDTH-mcu_x
        jack_lo, jack_hi = C.usb_jack_z(side)
        lo, hi = C.cover_usb_port_z(side)
        assert lo == pytest.approx(jack_lo-0.5)
        assert hi == pytest.approx(jack_hi+0.5)
        neck_y = north-C.COVER_NORTH_WALL/2
        assert (cover & _probe(x, neck_y, (lo+hi)/2)).volume < 1e-5
        outside_port = x + C.COVER_USB_PORT_W/2 + 0.25
        assert (cover & _probe(outside_port, north-0.25, (lo+hi)/2, 0.1)).volume > 1e-4
        # The jack is rectangular: the rounded port must keep clearance at its corners.
        jack_corner_x = x + C.USB_C_W/2 + 0.3
        jack_corner_z = jack_hi + 0.3
        assert (cover & _probe(jack_corner_x, north-0.25,
                               jack_corner_z, 0.1)).volume < 1e-5
        corner_x = x + C.COVER_USB_PORT_W/2 - 0.15
        corner_z = hi - 0.15
        assert (cover & _probe(corner_x, neck_y, corner_z, 0.12)).volume > 1e-4


def test_north_wall_is_flush_with_local_tray_rim(covers):
    local_outer = Tray._outer_poly_pts()[14][1]
    expected = (local_outer + C.WALL_THICKNESS + C.PCB_XY_CLEARANCE
                - C.RIM_FACET_RUN)
    assert MEC._north_landing_y() == pytest.approx(expected, abs=0.01)
    assert MEC._north_landing_y() < Tray._outer_extruded(0, 1).bounding_box().max.Y - 6
    assert max(y for _, y in MEC._cover_outer_polygon()) == pytest.approx(expected)
    for cover in covers.values():
        assert cover.bounding_box().max.Y == pytest.approx(expected, abs=0.01)


def test_west_edge_follows_local_tray_rim_and_keeps_mcu_clearance():
    west = min(x for x, _ in _cover_outer_polygon())
    local_tray_rim = (Tray._outer_poly_pts()[15][0] - C.WALL_THICKNESS
                      - C.PCB_XY_CLEARANCE + C.RIM_FACET_RUN)
    assert west == pytest.approx(local_tray_rim + C.COVER_WEST_OUTSET, abs=0.01)
    inner_west = min(x for x, _ in MEC._cover_inner_polygon())
    tray_inner_rim = Tray._outer_poly_pts()[15][0] - C.PCB_XY_CLEARANCE
    assert inner_west == pytest.approx(tray_inner_rim, abs=0.01)
    assert inner_west - west == pytest.approx(C.WALL_THICKNESS - C.RIM_FACET_RUN)
    mcu_west = C.pcb_to_case(*C.MCU_POS)[0] - C.MCU_WIDTH/2
    assert mcu_west - inner_west >= C.COVER_XY_CLEARANCE
    inner_north = max(y for _, y in MEC._cover_inner_polygon())
    assert inner_north - C.MCU_BODY_N_Y >= C.COVER_XY_CLEARANCE


def test_north_wall_has_no_installation_stop_below_rim(covers):
    north = MEC._north_landing_y()
    west = min(x for x, _ in _cover_outer_polygon())
    east = max(x for x, _ in _cover_outer_polygon())
    z0 = C.PCB_TOP_Z-0.1
    for side, cover in covers.items():
        left = west-1 if side == "right" else C.OUTER_WIDTH-east-1
        below_rim = Solid.make_box(east-west+2, 5, C.MAIN_RIM_Z-z0-0.01).translate(
            (left, north-3, z0))
        assert (cover & below_rim).volume < 1e-5
        assert cover.bounding_box().min.Z == pytest.approx(C.PCB_TOP_Z, abs=0.05)


def test_north_top_shoulder_has_case_style_two_to_one_draft(covers):
    north = max(y for _, y in _cover_outer_polygon())
    x = C.pcb_to_case(*C.MCU_POS)[0] - C.COVER_USB_PORT_W/2 - 2.0
    right = covers["right"]
    ridge = C.cover_ridge_top_z("right")
    # Outer half of the 0.5 mm run has dropped 0.5 mm; its old square corner is air.
    assert (right & _probe(x, north-0.1, ridge-0.2, 0.1)).volume < 1e-5
    # The same station remains solid below the 2:1 drafted shoulder.
    assert (right & _probe(x, north-0.1, ridge-0.9, 0.1)).volume > 1e-4


def test_west_and_east_shoulders_are_swept_facets_on_ramp_and_ridge(covers):
    right = covers["right"]
    west = min(x for x, _ in _cover_outer_polygon())
    east = max(x for x, _ in _cover_outer_polygon())
    for y in (77.0,
              C.COVER_RAMP_TOP_Y+10):
        roof = MEC._cover_roof_z(y, "right")
        for x, inward in ((west, 1), (east, -1)):
            assert (right & _probe(x+0.1*inward, y, roof-0.2, 0.1)).volume < 1e-5
            assert (right & _probe(x+0.1*inward, y, roof-2.35, 0.1)).volume > 1e-4


def test_side_chamfer_rotates_gradually_without_an_overlap_ridge(covers):
    west, east, _, _ = MEC._cover_wall_x_y()
    for side, cover in covers.items():
        for fraction in (0.1, 0.25, 0.5, 0.75, 0.9):
            y = C.COVER_RAMP_FOOT_Y+fraction*(C.COVER_RAMP_TOP_Y-C.COVER_RAMP_FOOT_Y)
            blend = fraction*fraction*(3-2*fraction)
            run = C.COVER_SOUTH_BEVEL+(C.COVER_SIDE_CHAMFER_RUN-C.COVER_SOUTH_BEVEL)*blend
            drop = C.COVER_SOUTH_BEVEL+(C.COVER_SIDE_CHAMFER_DROP-C.COVER_SOUTH_BEVEL)*blend
            roof = MEC._cover_roof_z(y, side)
            for wall, inward in ((west, 1), (east, -1)):
                for across in (0.25, 0.65):
                    x = wall+inward*run*across
                    if side == "left":
                        x = C.OUTER_WIDTH-x
                    surface_z = roof-drop*(1-across)
                    # One straight section across the bevel at each station; no second ridge.
                    assert (cover & _probe(x, y, surface_z+0.04, 0.02)).volume < 1e-7
                    assert (cover & _probe(x, y, surface_z-0.04, 0.02)).volume > 7.9e-6


def test_south_bevel_wraps_corners_and_connects_to_ramp_sides(covers):
    west, east, _, south = MEC._cover_wall_x_y()
    bevel = C.COVER_SOUTH_BEVEL
    foot = C.COVER_RAMP_FOOT_Y
    stations = []
    for x, inward in ((west, 1), (east, -1)):
        for y in (south+C.COVER_SOUTH_CORNER_CLIP+0.5,
                  (south+foot)/2, foot-0.2, foot+0.2, foot+2):
            stations.append((x+0.1*inward, y, MEC._cover_roof_z(y, "right")))
        clip = C.COVER_SOUTH_CORNER_CLIP
        stations.append((x+inward*(clip/2+0.1), south+clip/2+0.1, C.COVER_FOOT_Z))
    for side, cover in covers.items():
        for x, y, roof in stations:
            if side == "left":
                x = C.OUTER_WIDTH-x
                roof = MEC._cover_roof_z(y, "left")
            # The bevel removes the square top edge all the way through the junction.
            assert (cover & _probe(x, y, roof-0.1, 0.05)).volume < 1e-6
            # It remains a chamfer, not a slit through the side wall.
            assert (cover & _probe(x, y, roof-bevel-0.15, 0.05)).volume > 0.00012


@pytest.mark.parametrize("side", ["right", "left"])
def test_cover_retains_continuous_roof_over_actuator_access(covers, side):
    from sofle_case.slide_access import slide_finger_cutout

    cutter = slide_finger_cutout()
    bb = cutter.bounding_box()
    west = min(x for x, _ in _cover_outer_polygon())
    inner_west = min(x for x, _ in MEC._cover_inner_polygon())
    wall_end = min(bb.max.X, inner_west)
    mouth = Solid.make_box(
        wall_end - west, bb.size.Y,
        C.cover_ridge_top_z(side) + 2.0 - (C.MAIN_RIM_Z + 1.0),
    ).translate((west, bb.min.Y, C.MAIN_RIM_Z + 1.0))
    # Guard the actual post-shoulder top millimetre across the mounted pocket,
    # including its rounded southern edge, rather than a centerline datum.
    shell = MEC._shell(side)
    roof_web = (shell - shell.translate((0, 0, -1.0))) & mouth
    assert roof_web.volume > 1.0
    missing = (_sided(roof_web, side) - covers[side]).volume
    assert missing <= 1e-5, (
        f"{side} access removes roof material: {missing:.6f} mm³"
    )


@pytest.mark.parametrize("side", ["right", "left"])
def test_finger_access_preserves_bosses_outside_existing_can_relief(covers, side):
    from tests.test_clearances import _switch_can

    # The south boss already has a tiny can-clearance relief at its foot.
    # Exclude that independent hardware envelope, not the production cutter.
    can = _switch_can().bounding_box()
    relief = Solid.make_box(
        can.size.X + 1.0, can.size.Y + 1.0,
        C.MAIN_RIM_Z + 0.3 - (C.PCB_TOP_Z - 0.3),
    ).translate((can.min.X - 0.5, can.min.Y - 0.5, C.PCB_TOP_Z - 0.3))
    for point in MEC._th_positions("right"):
        protected = _sided(MEC._boss(point, side) - relief, side)
        assert (protected - covers[side]).volume <= 1e-5, (
            f"{side} access removes mounting-boss material at {point}"
        )


@pytest.mark.parametrize("side", ["right", "left"])
def test_complete_cover_clears_hardware_plate_case_and_nearby_switches(covers, side):
    from sofle_case.encoder_phantom import build_ec11
    from sofle_case.knob import place_knob
    from sofle_case.pcb_phantom import _mcu_block, _slide_switch_body, _usb_c_stub
    from sofle_case.plate_phantom import build_plate_phantom
    from sofle_case.switch_phantom import build_switch_phantom
    from tests.shared_builds import build_case_half
    def sided(part: Part) -> Part:
        return part if side == "right" else MEC._mirror_left(part)
    envelopes = {
        "encoder": sided(build_ec11()),
        "knob(bottomed)": sided(place_knob(bottomed=True)),
        "MCU": sided(_mcu_block()),
        "USB jack": sided(_usb_c_stub(side)),
        "slide switch": sided(_slide_switch_body()),
        "switch plate": sided(build_plate_phantom()),
        "case": build_case_half(side),
        "MX switches": sided(build_switch_phantom()),
    }
    for name, envelope in envelopes.items():
        assert (covers[side] & envelope).volume < 1e-5, f"{side} cover collides with {name}"


def test_encoder_sits_under_continuous_low_roof_with_shaft_exit(covers):
    right = covers["right"]
    x, y = C.pcb_to_case(*C.SW_ENCODER_POS)
    _, _, bbox_w, _ = MEC._encoder_bbox()
    cavity_half = bbox_w/2+C.COVER_ENCODER_CAVITY_CLEAR
    assert (right & _probe(x+cavity_half-0.2, y,
                           C.ENCODER_BODY_TOP_Z-0.2)).volume < 1e-5
    assert MEC._cover_roof_z(y, "right") == pytest.approx(C.COVER_FOOT_Z)
    assert (right & _probe(x, y, C.COVER_FOOT_Z-0.2)).volume < 1e-5
    assert (right & _probe(x + C.COVER_SHAFT_CUTOUT_DIA/2+0.8, y,
                           C.COVER_FOOT_Z-0.2)).volume > 0.005
    assert right.bounding_box().max.Z == pytest.approx(C.cover_ridge_top_z("right"), abs=0.05)


def test_left_right_footprints_are_mirrored_but_usb_heights_differ(covers):
    br, bl = covers["right"].bounding_box(), covers["left"].bounding_box()
    assert bl.min.X == pytest.approx(C.OUTER_WIDTH-br.max.X, abs=0.05)
    assert bl.max.X == pytest.approx(C.OUTER_WIDTH-br.min.X, abs=0.05)
    assert br.min.Y == pytest.approx(bl.min.Y, abs=0.05)
    assert br.max.Y == pytest.approx(bl.max.Y, abs=0.05)


def test_exported_stls_are_nonempty_and_source_parts_are_watertight(covers, tmp_path: Path):
    for side, cover in covers.items():
        path = tmp_path / f"sofle_cover_{side}.stl"
        export_stl(cover, str(path), tolerance=1e-3, angular_tolerance=0.05)
        assert path.stat().st_size > 1000
        assert cover.is_valid and len(cover.solids()) == 1
        raw = path.read_bytes()
        count = struct.unpack_from("<I", raw, 80)[0]
        assert len(raw) == 84 + count*50, "binary STL triangle stream is truncated"
        edge_counts: Counter[tuple[tuple[int, int, int], tuple[int, int, int]]] = Counter()
        for i in range(count):
            values = struct.unpack_from("<12fH", raw, 84+i*50)
            verts = [tuple(round(v*100_000) for v in values[j:j+3]) for j in (3, 6, 9)]
            for a, b in zip(verts, verts[1:]+verts[:1]):
                edge_counts[tuple(sorted((a, b)))] += 1
        assert edge_counts and set(edge_counts.values()) == {2}, "STL has open/non-manifold edges"
