"""Slide-switch bowl fit and flat-wall (no-hill) guarantees."""
from build123d import Axis, Solid
from sofle_case import constants as C
from sofle_case.tray import build_tray


def test_slide_scoop_opens_at_switch():
    """The finger scoop must open the −X wall at the actuator nub: material is gone at the wall
    centre at nub height, yet the wall stays solid below the scoop floor. Uses build_top_part —
    the scoop is a TOP-only, above-seam feature now (not in the shared build_tray).

    Probes the real wall centre (polygon PCB X=0 edge, case X ≈ 10.5) — not the PCB_X_MIN
    line (case X 0), which is air in front of the wall and passes even when the scoop is
    mislocated and removes nothing (the bug this guards against)."""
    from sofle_case.case import build_top_part
    top = build_top_part("right")
    _, cy = C.pcb_to_case(*C.SW_SLIDE_POS)
    wall_cx = C.pcb_to_case(0, 0)[0] - (C.WALL_THICKNESS + C.PCB_XY_CLEARANCE) / 2
    gone = Solid.make_box(1.0, 1.0, 1.0).translate(
        (wall_cx - 0.5, cy - 0.5, C.SLIDE_NUB_Z - 0.5)
    )
    assert (top & gone).volume < 0.01, (
        "scoop did not open the −X wall at the switch — mislocated or too narrow"
    )
    solid = Solid.make_box(1.0, 1.0, 1.0).translate(
        (wall_cx - 0.5, cy - 0.5, C.SLIDE_SCOOP_FLOOR_Z - 1.5)
    )
    assert (top & solid).volume > 0.1, "wall missing below the scoop floor"


def test_neg_x_wall_flat_at_mcu():
    """No hill: the −X wall over the MCU is flat at MAIN_RIM_Z, not raised."""
    tray = build_tray()
    _, mcu_cy = C.pcb_to_case(*C.MCU_POS)
    # At MCU Y the polygon left edge is the (0,0)→(0,-80.5) segment (PCB X=0),
    # not PCB_X_MIN which only applies at the board's bottom corners.
    poly_left_x = C.pcb_to_case(0.0, 0.0)[0]
    wall_center_x = poly_left_x - (C.WALL_THICKNESS + C.PCB_XY_CLEARANCE) / 2
    probe_z = C.MAIN_RIM_Z - 0.5
    probe = Solid.make_box(2.0, 2.0, 0.3).translate(
        (wall_center_x - 1.0, mcu_cy - 1.0, probe_z)
    )
    vol = (tray & probe).volume
    assert vol > 0.01, (
        f"−X wall has no material at MCU Y just below rim — wall may not reach MAIN_RIM_Z"
    )
    above_probe = Solid.make_box(2.0, 2.0, 0.3).translate(
        (wall_center_x - 1.0, mcu_cy - 1.0, C.MAIN_RIM_Z + 0.2)
    )
    above_vol = (tray & above_probe).volume
    assert above_vol < 0.01, (
        f"−X wall over MCU has material above rim — wall is not flat at MAIN_RIM_Z"
    )


def test_no_wall_above_rim():
    """All walls are flat at MAIN_RIM_Z — no feature (hill/ramp/relief) rises above it."""
    tray = build_tray()
    high = tray.edges().filter_by_position(Axis.Z, minimum=C.MAIN_RIM_Z + 0.5, maximum=999)
    assert len(high) == 0, f"{len(high)} edges above the rim — walls are not flat"


def test_slide_scoop_floor_above_pcb():
    """Scoop floor sits above the PCB top (doesn't gouge to the PCB) yet below the nub."""
    assert C.PCB_TOP_Z <= C.SLIDE_SCOOP_FLOOR_Z < C.SLIDE_NUB_Z, (
        f"scoop floor {C.SLIDE_SCOOP_FLOOR_Z} not between PCB top {C.PCB_TOP_Z} and nub {C.SLIDE_NUB_Z}"
    )
