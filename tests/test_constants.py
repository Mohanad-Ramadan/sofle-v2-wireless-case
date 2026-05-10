"""Sanity checks on dimension constants."""
from sofle_case import constants as C


def test_z_stack_monotonic():
    """Z layers must increase: floor < pcb_seat < pcb_top < plate_seat < plate_top < rim."""
    z = [
        C.FLOOR_THICKNESS,
        C.PCB_SEAT_Z,
        C.PCB_TOP_Z,
        C.PLATE_SEAT_Z,
        C.PLATE_TOP_Z,
        C.MAIN_RIM_Z,
    ]
    assert z == sorted(z), f"Z stack not monotonic: {z}"


def test_pcb_thickness_consistent():
    assert C.PCB_TOP_Z - C.PCB_SEAT_Z == C.PCB_THICKNESS


def test_plate_thickness_consistent():
    assert C.PLATE_TOP_Z - C.PLATE_SEAT_Z == C.PLATE_THICKNESS


def test_outer_envelope_fits_pcb():
    PCB_W, PCB_D = 143.5, 115.5
    assert C.OUTER_WIDTH >= PCB_W + 2 * C.WALL_THICKNESS + 2 * C.PCB_XY_CLEARANCE
    assert C.OUTER_DEPTH >= PCB_D + 2 * C.WALL_THICKNESS + 2 * C.PCB_XY_CLEARANCE


def test_standoff_passes_pcb_hole():
    assert C.STANDOFF_OD_UPPER < C.PCB_HOLE_DIA
    assert C.STANDOFF_OD_LOWER > C.PCB_HOLE_DIA  # shoulder must catch PCB


def test_five_mounting_holes():
    assert len(C.MOUNTING_HOLES) == 5


def test_mcu_stack_order():
    """MCU stack Z values must be monotonically increasing.

    Note: USB_C_BODY_TOP_Z exceeds MAIN_RIM_Z by design — the USB-C cutout
    punches past the wall rim so a single STL fits both PCB halves.
    """
    assert C.PCB_TOP_Z < C.MCU_PCB_TOP_Z < C.USB_C_BODY_TOP_Z
