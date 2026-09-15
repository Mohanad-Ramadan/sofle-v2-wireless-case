"""Tests that the tray walls strictly follow the PCB frame (uniform WALL).

The former MCU +Y relief (bump+ widen) has been removed: the MCU on tall
headers sits ~4.4 mm above the rim, so no wall cut is needed. Outer =
offset(WALL+CLEARANCE), inner = offset(CLEARANCE), WALL=4.75 continuous.
The plate notch (switch-plate vs PCB area) remains open — tested in
test_monolithic_case.py and not touched here.
"""
from build123d import Solid

from sofle_case import constants as C
from tests.shared_builds import build_tray


def _z_mid() -> float:
    """Comfortably inside the wall span (floor to MAIN_RIM_Z)."""
    return (C.FLOOR_THICKNESS + C.MAIN_RIM_Z) / 2


def test_tray_still_single_solid():
    """Tray must remain one fused solid after removing the relief."""
    t = build_tray()
    assert len(t.solids()) == 1, f"tray has {len(t.solids())} solids; expected 1 fused solid"


def test_plus_y_face_bumped_out():
    """Outer +Y wall is at the standard PCB-frame offset, not at the old relieved target."""
    t = build_tray()
    x_mid = C.pcb_to_case(C.MCU_POS[0], 0)[0]
    standard_outer = C.pcb_to_case(0, 0)[1] + C.WALL_THICKNESS + C.PCB_XY_CLEARANCE
    relieved_outer = C.pcb_to_case(0, C.MCU_Y_RELIEF_TARGET_Y)[1] + C.WALL_THICKNESS + C.PCB_XY_CLEARANCE
    # Standard outer must be solid wall
    probe_std = Solid.make_box(2.0, 1.0, 2.0).translate((x_mid, standard_outer - 1.0, _z_mid()))
    assert (t & probe_std).volume > 0, "no solid material at standard +Y outer wall position"
    # Relieved target (2.5 mm further north) must be air
    probe_rel = Solid.make_box(2.0, 1.0, 2.0).translate((x_mid, relieved_outer - 1.0, _z_mid()))
    assert (t & probe_rel).volume == 0, "relieved +Y target still solid — wall did not follow PCB frame"


def test_plus_y_cavity_widened():
    """Old +Y wall zone (just north of inner face) must be solid wall, not hollow widen."""
    t = build_tray()
    x_mid = C.pcb_to_case(C.MCU_POS[0], 0)[0]
    old_inner_y = C.pcb_to_case(0, 0)[1] + C.PCB_XY_CLEARANCE
    probe = Solid.make_box(2.0, 0.5, 2.0).translate((x_mid, old_inner_y + 0.1, _z_mid()))
    assert (t & probe).volume > 0, "old +Y wall zone hollow — wall should be continuous"
    # Also ensure the probe is substantially filled (wall, not sliver)
    full = 2.0 * 0.5 * 2.0
    assert (t & probe).volume > full * 0.5, "wall not continuous at former widen zone"


def test_north_wall_closes_only_beyond_mcu_clearance():
    """Bay between MCU north edge and standard north wall is closed by continuous wall."""
    t = build_tray()
    x_mid = C.pcb_to_case(C.MCU_POS[0], 0)[0]
    # With uniform wall, the wall itself spans standard inner..outer (116.25..121).
    # Probe in the middle of the wall thickness over the MCU X must be solid.
    standard_inner = C.pcb_to_case(0, 0)[1] + C.PCB_XY_CLEARANCE
    standard_outer = standard_inner + C.WALL_THICKNESS
    probe = Solid.make_box(2.0, 0.4, 1.0).translate(
        (x_mid - 1.0, (standard_inner + standard_outer) / 2 - 0.2, _z_mid())
    )
    assert (t & probe).volume > 0.95 * probe.volume, "north wall not continuous — gap where widen was"


def test_relief_reaches_rim():
    """Standard +Y wall reaches full height; relieved target does not (air above rim)."""
    t = build_tray()
    x_mid = C.pcb_to_case(C.MCU_POS[0], 0)[0]
    standard_outer = C.pcb_to_case(0, 0)[1] + C.WALL_THICKNESS + C.PCB_XY_CLEARANCE
    relieved_outer = C.pcb_to_case(0, C.MCU_Y_RELIEF_TARGET_Y)[1] + C.WALL_THICKNESS + C.PCB_XY_CLEARANCE
    z_full = C.MAIN_RIM_Z - C.RIM_FACET_DROP - 0.5  # below facet, full thickness
    probe_std = Solid.make_box(2.0, 1.0, 1.0).translate((x_mid, standard_outer - 1.0, z_full))
    assert (t & probe_std).volume > 0, "standard +Y wall does not reach rim"
    probe_rel = Solid.make_box(2.0, 1.0, 1.0).translate((x_mid, relieved_outer - 1.0, z_full))
    assert (t & probe_rel).volume == 0, "relieved outer still solid at rim — wall should follow PCB frame"


def test_minus_x_wall_untouched():
    """−X wall remains solid along its whole strip; no corner punch."""
    t = build_tray()
    corner_x = C.pcb_to_case(0, 0)[0]
    x_outer = corner_x - C.WALL_THICKNESS - C.PCB_XY_CLEARANCE
    for y in (80.0, 90.0, 100.0, 108.0, 112.0):
        probe = Solid.make_box(C.WALL_THICKNESS, 2.0, 2.0).translate((x_outer, y, C.MAIN_RIM_Z - 3.0))
        full = C.WALL_THICKNESS * 2.0 * 2.0
        assert (t & probe).volume > full * 0.5, f"−X wall thinned/holed at Y={y}"


def test_wall_thickness_preserved():
    """Wall thickness is uniform WALL at the standard PCB-frame offset."""
    standard_outer = C.pcb_to_case(0, 0)[1] + C.WALL_THICKNESS + C.PCB_XY_CLEARANCE
    standard_inner = C.pcb_to_case(0, 0)[1] + C.PCB_XY_CLEARANCE
    assert abs((standard_outer - standard_inner) - C.WALL_THICKNESS) < 0.01
    # Physical check: probe inside wall vs cavity
    t = build_tray()
    x_mid = C.pcb_to_case(C.MCU_POS[0], 0)[0]
    mid_y = (standard_inner + standard_outer) / 2
    probe_wall = Solid.make_box(1.0, 0.5, 1.0).translate((x_mid, mid_y - 0.25, _z_mid()))
    assert (t & probe_wall).volume > 0.9 * probe_wall.volume, "wall not uniform thickness at standard offset"
    probe_cavity = Solid.make_box(1.0, 0.5, 1.0).translate((x_mid, standard_inner - 1.0, _z_mid()))
    assert (t & probe_cavity).volume == 0, "cavity should be hollow just inside standard inner face"
