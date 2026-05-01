"""Switch plate phantom geometry checks."""
from build123d import Part
from sofle_case import constants as C
from sofle_case.plate_phantom import build_plate_phantom


def test_returns_part():
    assert isinstance(build_plate_phantom(), Part)


def test_z_min_at_plate_seat():
    bb = build_plate_phantom().bounding_box()
    assert abs(bb.min.Z - C.PLATE_SEAT_Z) < 0.1


def test_z_max_at_plate_top():
    bb = build_plate_phantom().bounding_box()
    assert abs(bb.max.Z - C.PLATE_TOP_Z) < 0.1


def test_volume_less_than_bbox():
    """Switch holes + mounting holes → phantom volume < solid bounding box."""
    phantom = build_plate_phantom()
    bb = phantom.bounding_box()
    bbox_vol = (
        (bb.max.X - bb.min.X)
        * (bb.max.Y - bb.min.Y)
        * (bb.max.Z - bb.min.Z)
    )
    assert phantom.volume < bbox_vol


def test_plate_above_pcb():
    """PLATE_SEAT_Z must be above PCB_TOP_Z (there is a gap)."""
    assert C.PLATE_SEAT_Z > C.PCB_TOP_Z
