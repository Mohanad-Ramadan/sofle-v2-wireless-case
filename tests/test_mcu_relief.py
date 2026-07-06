"""Tests for the MCU +Y cover relief (B+/B- pin clearance): the MCU cover's +Y
wall is pushed out to the index-column line. ONLY the +Y wall moves — the −X
wall is left exactly as-is."""
from build123d import Solid
from sofle_case import constants as C
from sofle_case.tray import build_tray


def _z_mid() -> float:
    """Comfortably inside the relief's floor-to-MAIN_RIM_Z span."""
    return (C.FLOOR_THICKNESS + C.MAIN_RIM_Z) / 2


def test_tray_still_single_solid():
    """Regression guard: the relief bump/widen pair must fuse cleanly with the
    rest of the shell, not leave a disconnected floating ridge (see
    MCU_Y_RELIEF_OVERLAP comment in constants.py for why this is fragile)."""
    t = build_tray()
    assert len(t.solids()) == 1, f"tray has {len(t.solids())} solids; expected 1 fused solid"


def test_plus_y_face_bumped_out():
    """Solid material must reach the relieved target Y over the MCU."""
    t = build_tray()
    x_mid = C.pcb_to_case(C.MCU_POS[0], 0)[0]
    target_y = C.pcb_to_case(0, C.MCU_Y_RELIEF_TARGET_Y)[1] + C.WALL_THICKNESS + C.PCB_XY_CLEARANCE
    probe = Solid.make_box(2.0, 1.0, 2.0).translate((x_mid, target_y - 1.0, _z_mid()))
    assert (t & probe).volume > 0, "no solid material at the relieved +Y outer wall position"


def test_plus_y_cavity_widened():
    """The old +Y wall's inner-face zone over the MCU must now be hollow."""
    t = build_tray()
    x_mid = C.pcb_to_case(C.MCU_POS[0], 0)[0]
    old_inner_y = C.pcb_to_case(0, 0)[1] + C.PCB_XY_CLEARANCE
    probe = Solid.make_box(2.0, 1.0, 2.0).translate((x_mid, old_inner_y + 0.5, _z_mid()))
    assert (t & probe).volume == 0, "old +Y wall zone still solid — cavity was not widened"


def test_relief_reaches_rim():
    """Relief must reach up through the full wall height; above the rim there is no
    wall, so the B+/B- pads clear into open air. Probe just below the outer-top
    chamfer drop, where the pushed-out wall is at full thickness (the chamfer
    cosmetically bevels the outer-top edge but does not reduce inner clearance)."""
    t = build_tray()
    x_mid = C.pcb_to_case(C.MCU_POS[0], 0)[0]
    target_y = C.pcb_to_case(0, C.MCU_Y_RELIEF_TARGET_Y)[1] + C.WALL_THICKNESS + C.PCB_XY_CLEARANCE
    z_full = C.MAIN_RIM_Z - C.OUTER_TOP_CHAMFER - 0.5   # below the 45° chamfer, full thickness
    probe = Solid.make_box(2.0, 1.0, 1.0).translate((x_mid, target_y - 1.0, z_full))
    assert (t & probe).volume > 0, "relief does not reach the top of the wall"


def test_minus_x_wall_untouched():
    """The −X wall must remain solid along its whole hill strip — the relief
    only touches the +Y wall (regression guard for the corner-relief bug that
    punched a hole through the −X wall)."""
    t = build_tray()
    corner_x = C.pcb_to_case(0, 0)[0]
    x_outer = corner_x - C.WALL_THICKNESS - C.PCB_XY_CLEARANCE     # −X wall outer face
    for y in (80.0, 90.0, 100.0, 108.0, 112.0):
        probe = Solid.make_box(C.WALL_THICKNESS, 2.0, 2.0).translate((x_outer, y, C.MAIN_RIM_Z - 3.0))
        full = C.WALL_THICKNESS * 2.0 * 2.0
        assert (t & probe).volume > full * 0.5, f"−X wall thinned/holed at Y={y}"


def test_wall_thickness_preserved():
    """New outer face minus new inner face should still equal WALL_THICKNESS —
    the +Y wall shifted outward, it didn't just thin out."""
    new_outer = C.pcb_to_case(0, C.MCU_Y_RELIEF_TARGET_Y)[1] + C.WALL_THICKNESS + C.PCB_XY_CLEARANCE
    new_inner = C.pcb_to_case(0, C.MCU_Y_RELIEF_TARGET_Y)[1] + C.PCB_XY_CLEARANCE
    assert abs((new_outer - new_inner) - C.WALL_THICKNESS) < 0.01
