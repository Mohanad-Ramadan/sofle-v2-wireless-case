"""Retained slide-switch access features."""

from sofle_case import constants as C
from sofle_case.case import _slide_actuator_cavity, _slide_scoop


def test_slide_cutters_are_single_solids():
    for cutter in (_slide_scoop(), _slide_actuator_cavity()):
        assert cutter.volume > 0
        assert len(cutter.solids()) == 1


def test_actuator_cavity_uses_hardware_z_band():
    bb = _slide_actuator_cavity().bounding_box()
    assert abs(bb.min.Z - (C.PCB_TOP_Z - 0.3)) < 0.01
    assert abs(bb.max.Z - (C.PCB_TOP_Z + C.SLIDE_ACTUATOR_BODY_H + 0.3)) < 0.01


def test_actuator_cavity_does_not_cut_floor():
    assert _slide_actuator_cavity().bounding_box().min.Z > 0.0
