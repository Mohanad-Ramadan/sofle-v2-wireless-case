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


def test_z_ladder_derives_from_floor():
    """The whole Z stack must track FLOOR_THICKNESS via the named gaps, so a floor
    change cascades correctly (guards against reintroducing hardcoded literals)."""
    assert C.PCB_SEAT_Z == C.FLOOR_THICKNESS + C.STANDOFF_SHOULDER_H
    assert C.PCB_TOP_Z == C.PCB_SEAT_Z + C.PCB_THICKNESS
    assert C.PLATE_SEAT_Z == C.PCB_TOP_Z + C.MX_BODY_CLEAR
    assert C.PLATE_TOP_Z == C.PLATE_SEAT_Z + C.PLATE_THICKNESS


def test_pcb_thickness_consistent():
    assert abs((C.PCB_TOP_Z - C.PCB_SEAT_Z) - C.PCB_THICKNESS) < 1e-9


def test_plate_thickness_consistent():
    assert abs((C.PLATE_TOP_Z - C.PLATE_SEAT_Z) - C.PLATE_THICKNESS) < 1e-9


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

    The jack bands exceed MAIN_RIM_Z by design — the port punches through the canopy's
    north wall, which stands above the rim.
    """
    assert C.PCB_TOP_Z < C.MCU_PCB_TOP_Z < C.USB_JACK_NEUTRAL_HI_Z


def test_usb_jack_bands_are_measured_values():
    """Caliper-measured, referenced to the main PCB top face. Both bands are the same
    4.0 mm connector; they abut at the nano board's underside (20.4)."""
    assert C.usb_jack_z("left") == (C.PCB_TOP_Z + 6.0, C.PCB_TOP_Z + 10.0)    # flipped
    assert C.usb_jack_z("right") == (C.PCB_TOP_Z + 10.0, C.PCB_TOP_Z + 14.0)  # neutral
    for side in ("left", "right"):
        lo, hi = C.usb_jack_z(side)
        assert abs((hi - lo) - C.USB_JACK_H) < 1e-9
    assert C.usb_jack_z("left")[1] == C.usb_jack_z("right")[0], "bands must abut"


def test_usb_jack_z_rejects_bad_side():
    import pytest as _pt
    with _pt.raises(ValueError):
        C.usb_jack_z("middle")


def test_mcu_orientation_mapping():
    """Assembly-time fact: left half carries a flipped nano, right a neutral one."""
    assert C.MCU_ORIENTATION == {"left": "flipped", "right": "neutral"}
