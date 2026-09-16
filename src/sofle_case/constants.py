"""Physical dimensions and shared datums for the monolithic Sofle case (millimetres)."""
from __future__ import annotations

from typing import Literal

# Z stack. The printable rim is exactly coplanar with the switch-plate top.
FLOOR_THICKNESS = 6.6
STANDOFF_SHOULDER_H = 2.5
PCB_THICKNESS = 1.6
PLATE_THICKNESS = 1.6
MX_BODY_CLEAR = 3.4
PCB_SEAT_Z = FLOOR_THICKNESS + STANDOFF_SHOULDER_H
PCB_TOP_Z = PCB_SEAT_Z + PCB_THICKNESS
PLATE_SEAT_Z = PCB_TOP_Z + MX_BODY_CLEAR
PLATE_TOP_Z = PLATE_SEAT_Z + PLATE_THICKNESS
MAIN_RIM_Z = PLATE_TOP_Z

# PCB envelope and case wall.
PCB_X_MIN, PCB_X_MAX = -8.5, 135.0
PCB_Y_MIN, PCB_Y_MAX = -110.5, 5.0
PCB_XY_CLEARANCE = 0.2
WALL_THICKNESS = 4.75
OUTER_WIDTH = (PCB_X_MAX - PCB_X_MIN) + 2 * (WALL_THICKNESS + PCB_XY_CLEARANCE)
OUTER_DEPTH = (PCB_Y_MAX - PCB_Y_MIN) + 2 * (WALL_THICKNESS + PCB_XY_CLEARANCE)
BOTTOM_CHAMFER = 0.5

PCB_OFFSET_X = (OUTER_WIDTH - (PCB_X_MAX - PCB_X_MIN)) / 2 - PCB_X_MIN
PCB_OFFSET_Y = (OUTER_DEPTH - (PCB_Y_MAX - PCB_Y_MIN)) / 2 - PCB_Y_MIN


def pcb_to_case(x: float, y: float) -> tuple[float, float]:
    """Convert a PCB-coordinate point to right-hand case coordinates."""
    return x + PCB_OFFSET_X, y + PCB_OFFSET_Y


# PCB mounting and retained hardware positions.
MOUNTING_HOLES: tuple[tuple[float, float], ...] = (
    (14.07, -80.26), (39.57, -19.05), (39.57, -56.96),
    (116.07, -25.66), (116.07, -63.96),
)
PCB_HOLE_DIA = 4.1
MCU_POS = (10.27, -16.16)
SW_SLIDE_POS = (2.945, -45.23)
SW_ENCODER_POS = (9.47, -65.95)

# nice!nano/SuperMini physical envelope and orientation.
MCU_WIDTH = 18.0
MCU_BODY_L = 34.1
MCU_BOARD_THK = 1.6
MCU_PIN_SPAN_Y = 27.94
MCU_PIN_TO_SOUTH_EDGE = 2.54
MCU_PCB_TOP_Z = PCB_TOP_Z + 11.0
MCU_PCB_BOT_Z = MCU_PCB_TOP_Z - MCU_BOARD_THK
MCU_BODY_S_Y = pcb_to_case(*MCU_POS)[1] - MCU_PIN_SPAN_Y / 2 - MCU_PIN_TO_SOUTH_EDGE
MCU_BODY_N_Y = MCU_BODY_S_Y + MCU_BODY_L
MCU_ORIENTATION = {"left": "flipped", "right": "neutral"}
MCU_Y_RELIEF_TARGET_Y = 2.5
MCU_Y_RELIEF_X_HI = 41.0
MCU_Y_RELIEF_OVERLAP = 1.0
MCU_Y_RELIEF_CEILING_X = 20.0
BAY_NORTH_INNER_Y = pcb_to_case(0, MCU_Y_RELIEF_TARGET_Y)[1] + PCB_XY_CLEARANCE

# USB-C mid-mount band, retained for the hardware phantom.
USB_C_W = 9.0
USB_JACK_H = 3.16
USB_JACK_SINK = 1.0
USB_JACK_PROUD = USB_JACK_H - USB_JACK_SINK
USB_JACK_Y_PROTRUDE = 1.0
USB_PORT_CLEAR_LO = 0.8
USB_PORT_CLEAR_HI = 0.7
USB_JACK_NEUTRAL_LO_Z = MCU_PCB_TOP_Z - USB_JACK_SINK
USB_JACK_NEUTRAL_HI_Z = MCU_PCB_TOP_Z + USB_JACK_PROUD
USB_JACK_FLIPPED_LO_Z = MCU_PCB_BOT_Z - USB_JACK_PROUD
USB_JACK_FLIPPED_HI_Z = MCU_PCB_BOT_Z + USB_JACK_SINK


def usb_jack_z(side: Literal["left", "right"] | str) -> tuple[float, float]:
    if side == "left":
        return USB_JACK_FLIPPED_LO_Z, USB_JACK_FLIPPED_HI_Z
    if side == "right":
        return USB_JACK_NEUTRAL_LO_Z, USB_JACK_NEUTRAL_HI_Z
    raise ValueError(f"side must be 'left' or 'right', got {side!r}")


def usb_port_z(side: Literal["left", "right"] | str) -> tuple[float, float]:
    lo, hi = usb_jack_z(side)
    return lo - USB_PORT_CLEAR_LO, hi + USB_PORT_CLEAR_HI


# Retained slide-switch clearance, including its 0.5 mm XY pad.
SLIDE_ACTUATOR_BODY_H = 4.3
SLIDE_ACTUATOR_BODY_L = 8.7
SLIDE_ACTUATOR_BODY_W = 4.4
SLIDE_ACTUATOR_NUB_L = 3.5
SLIDE_ACTUATOR_NUB_D = 3.0
SLIDE_ACTUATOR_NUB_BASE = 1.5
SLIDE_ACTUATOR_NUB_H = 2.0
SLIDE_ACTUATOR_PIN_CENTER_X = 2.0
SLIDE_ACTUATOR_PAD = 0.5
SLIDE_NUB_Z = PCB_TOP_Z + SLIDE_ACTUATOR_NUB_BASE + SLIDE_ACTUATOR_NUB_H / 2
SLIDE_SCOOP_FLOOR_Z = SLIDE_NUB_Z - 1.4
SLIDE_SCOOP_FLOOR_R = 2.0
SLIDE_SCOOP_W = 8.0
SLIDE_SCOOP_X_SHIFT = 0.4
# Extend the scoop just past the wall's inner face so it opens cleanly to the
# rim instead of leaving a thin overhead lip on the actuator side.
SLIDE_SCOOP_INNER_MARGIN = 1

# Battery and JST recesses.
BATTERY_POCKET_POS = (69.5, -48.5)
BATTERY_W, BATTERY_L = 50.0, 70.0
BATTERY_THICKNESS = 4.5
BATTERY_XY_CLEARANCE = 1.5
BATTERY_POCKET_SHIFT_X = 1.0
BATTERY_Z_CLEARANCE = 0.3
BATTERY_FLOOR_BASE = 2.0
BATTERY_POCKET_DEPTH = FLOOR_THICKNESS - BATTERY_FLOOR_BASE
BATTERY_POCKET_CORNER_R = 2.0

JST_POS = (12.855, -48.735)
JST_PIN_PITCH = 2.54
JST_MOUNT_W, JST_MOUNT_E = 0.5, 1.5
JST_BODY_H, JST_BODY_W, JST_BODY_D = 6.5, 8.0, 8.0
JST_PLUG_RUN = 6.3
JST_WIRE_BEND = 3.0
JST_BOTTOM_Z = PCB_SEAT_Z - JST_BODY_H
JST_POCKET_PAD = 0.5
JST_POCKET_FLOOR_Z = JST_BOTTOM_Z - 0.5
JST_POCKET_DEPTH = FLOOR_THICKNESS - JST_POCKET_FLOOR_Z
JST_POCKET_CORNER_R = 1.5
JST_CHANNEL_W = 5.0
JST_CHANNEL_FLOOR_Z = JST_POCKET_FLOOR_Z
JST_CHANNEL_DEPTH = FLOOR_THICKNESS - JST_CHANNEL_FLOOR_Z
JST_CHANNEL_TOP_Y = 90.0
JST_CHANNEL_MID_X = 44.0
JST_CHANNEL_BAT_INSET = JST_CHANNEL_W / 2

# Underside feet.
FOOT_DEPTH = 0.6
FOOT_DIA = 10.0
FOOT_POSITIONS: tuple[tuple[float, float], ...] = (
    (20.5, 108.5), (141.75, 102.75), (21.0, 23.0), (142.5, 39.75),
)

# EC11 hardware phantom only; these dimensions are not structural geometry.
ENCODER_BODY_H = 7.0
ENCODER_BODY_TOP_Z = PCB_TOP_Z + ENCODER_BODY_H
ENCODER_LEG_H = 0.8

# Protected south styling.
SOUTH_WALL_EXTRA = 3.0
FRONT_FACET_RUN = 6.0
FRONT_FACET_DROP = 8.8
FRONT_FACET_Y_MASK = 22.0
FRONT_CREASE_END_MARGIN = 2.0
REFLEX_ROUND_R = 2.0
FRONT_CORNER_ROUND_R = 3.0
RIM_FACET_RUN = 2.0
RIM_FACET_DROP = 4.0

# Historical M2 bosses.
STANDOFF_OD_LOWER = 5.5
STANDOFF_OD_UPPER = 3.9
STANDOFF_TAP_DIA = 1.8
STANDOFF_BORE_DEPTH = 4.0
STANDOFF_BORE_CHAMFER = 0.3
