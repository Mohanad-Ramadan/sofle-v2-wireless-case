"""PCB phantom geometry checks."""
from build123d import Part
from sofle_case import constants as C
from sofle_case.pcb_phantom import build_pcb_phantom


def test_returns_part():
    assert isinstance(build_pcb_phantom(), Part)


def test_z_min_at_pcb_seat():
    bb = build_pcb_phantom().bounding_box()
    assert abs(bb.min.Z - C.PCB_SEAT_Z) < 0.1


def test_z_max_at_usb_c_body_top():
    bb = build_pcb_phantom().bounding_box()
    assert abs(bb.max.Z - C.USB_C_BODY_TOP_Z) < 0.1


def test_volume_less_than_bbox():
    """M2 holes + partial fill → phantom volume < solid bounding box."""
    phantom = build_pcb_phantom()
    bb = phantom.bounding_box()
    bbox_vol = (
        (bb.max.X - bb.min.X)
        * (bb.max.Y - bb.min.Y)
        * (bb.max.Z - bb.min.Z)
    )
    assert phantom.volume < bbox_vol
