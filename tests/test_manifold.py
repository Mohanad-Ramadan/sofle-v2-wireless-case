from tests.shared_builds import build_case_half


def test_left_is_valid():
    p = build_case_half("left")
    assert p.is_valid, "left half failed BRepCheck"


def test_right_is_valid():
    p = build_case_half("right")
    assert p.is_valid, "right half failed BRepCheck"
