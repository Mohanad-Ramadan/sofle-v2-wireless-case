"""Moderate concave access without a stepped pocket or pinched approach."""

from build123d import Plane, section

from sofle_case import constants as C
from sofle_case.slide_access import slide_finger_cutout
from tests.test_clearances import _nub_center


def test_shared_finger_cutout_is_one_valid_solid():
    cutter = slide_finger_cutout()
    assert cutter.is_valid
    assert len(cutter.solids()) == 1


def test_concave_port_is_moderate_at_the_control_and_has_no_step():
    nx, _ = _nub_center()
    front = nx - C.SLIDE_ACTUATOR_NUB_D / 2
    outside = C.pcb_to_case(0, 0)[0] - C.WALL_THICKNESS - C.PCB_XY_CLEARANCE
    cutter = slide_finger_cutout()
    entry, control = [
        section(cutter, section_by=Plane.YZ.offset(x)).bounding_box()
        for x in (outside, front)
    ]
    assert 9.25 <= control.size.Y < entry.size.Y
    assert entry.min.Z < control.min.Z
    # A height/width jump survives shrinking the sample interval. A concave
    # surface converges continuously, including the former back-wall location.
    for x in (front, front + 0.4):
        differences = []
        for distance in (0.01, 0.001):
            before, after = [
                section(cutter, section_by=Plane.YZ.offset(point)).bounding_box()
                for point in (x - distance, x + distance)
            ]
            differences.append((abs(before.min.Z - after.min.Z),
                                abs(before.size.Y - after.size.Y)))
        for coarse, fine in zip(*differences):
            assert fine <= 0.2 * coarse + 1e-6
