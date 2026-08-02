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


def test_usb_jack_bands_derive_from_the_board_faces():
    """Both bands are the SAME mid-mount shell, straddling whichever board face the nano's
    components point at: USB_JACK_SINK below it, USB_JACK_PROUD above it.

    Neutral (components up) references the board TOP, flipped (components down) the board
    UNDERSIDE. The bands do NOT abut — an earlier revision asserted they met exactly at
    20.4, but that was an artifact of a guessed 4.0 mm shell, not geometry.
    """
    assert C.usb_jack_z("right") == (C.MCU_PCB_TOP_Z - C.USB_JACK_SINK,
                                     C.MCU_PCB_TOP_Z + C.USB_JACK_PROUD)   # neutral
    assert C.usb_jack_z("left") == (C.MCU_PCB_BOT_Z - C.USB_JACK_PROUD,
                                    C.MCU_PCB_BOT_Z + C.USB_JACK_SINK)     # flipped
    for side in ("left", "right"):
        lo, hi = C.usb_jack_z(side)
        assert abs((hi - lo) - C.USB_JACK_H) < 1e-9


def test_usb_jack_is_mid_mount_not_top_mount():
    """The shell straddles the board — it must poke out BOTH faces, or the constants have
    silently reverted to a top-mount part (3.46 mm sitting wholly on the board)."""
    assert 0 < C.USB_JACK_SINK < C.USB_JACK_H, "sink must be inside the shell height"
    assert C.USB_JACK_SINK < C.MCU_BOARD_THK, "shell would punch clean through the board"
    for side in ("left", "right"):
        lo, hi = C.usb_jack_z(side)
        assert lo < C.MCU_PCB_TOP_Z < hi or lo < C.MCU_PCB_BOT_Z < hi


def test_mcu_board_is_anchored_to_its_pin_array_not_centred_on_it():
    """The nano is located by its 24 pin holes (``MCU_POS`` = the array centre, verified
    against data/raw/SofleKeyboard-PTH.drl), so its USB-end face must derive from the
    northmost pin — NEVER from ``MCU_POS ± MCU_BODY_L/2``.

    The centred form agreed by luck while MCU_BODY_L was the nice!nano's 33.0, which is
    centred on the 27.94 pin span. At the SuperMini's 34.1 it walks the USB end 0.55 mm
    north and invents a collision with the canopy wall. Growing MCU_BODY_L must extend the
    SOUTH end only.
    """
    assert abs(C.MCU_BODY_N_Y - 116.09) < 1e-6, "USB-end face moved — jack/wall gap is at risk"
    assert abs((C.MCU_BODY_N_Y - C.MCU_BODY_S_Y) - C.MCU_BODY_L) < 1e-9
    centred = C.pcb_to_case(*C.MCU_POS)[1] + C.MCU_BODY_L / 2
    assert C.MCU_BODY_N_Y < centred, "board is being centred on MCU_POS again"


def test_usb_jack_z_rejects_bad_side():
    import pytest as _pt
    with _pt.raises(ValueError):
        C.usb_jack_z("middle")


def test_usb_port_z_is_jack_band_plus_clears():
    """The printed port band is the measured jack band grown by the USB_PORT_CLEAR_*
    design margins — and nothing else. Guards the constants.py single-source split
    (canopy.canopy_usb_z delegates here)."""
    for side in ("left", "right"):
        jlo, jhi = C.usb_jack_z(side)
        plo, phi = C.usb_port_z(side)
        assert plo == jlo - C.USB_PORT_CLEAR_LO
        assert phi == jhi + C.USB_PORT_CLEAR_HI
        # 3.16 jack + 0.8 + 0.7 = 4.66 mm mouth on BOTH halves.
        assert abs((phi - plo) - (C.USB_JACK_H + C.USB_PORT_CLEAR_LO + C.USB_PORT_CLEAR_HI)) < 1e-9


def test_usb_port_z_rejects_bad_side():
    import pytest as _pt
    with _pt.raises(ValueError):
        C.usb_port_z("middle")


def test_mcu_orientation_mapping():
    """Assembly-time fact: left half carries a flipped nano, right a neutral one."""
    assert C.MCU_ORIENTATION == {"left": "flipped", "right": "neutral"}
