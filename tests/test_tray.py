"""Tray (shell + cavity) tests."""
from build123d import Part
from sofle_case import constants as C
from sofle_case.tray import build_tray


def test_returns_part():
    t = build_tray()
    assert isinstance(t, Part)


def test_outer_bbox():
    t = build_tray()
    bb = t.bounding_box()
    assert abs((bb.max.X - bb.min.X) - C.OUTER_WIDTH) < 0.01
    assert abs((bb.max.Y - bb.min.Y) - C.OUTER_DEPTH) < 0.01
    assert abs(bb.min.Z - 0.0) < 0.01
    assert abs(bb.max.Z - C.MCU_HILL_Z) < 0.01


def test_volume_smaller_than_solid_box():
    """Hollow tray < solid box of the same outer dims."""
    t = build_tray()
    solid_vol = C.OUTER_WIDTH * C.OUTER_DEPTH * C.MAIN_RIM_Z
    assert t.volume < solid_vol * 0.7


def test_mcu_hill_plus_y_wall_raised():
    """+Y wall has edges above MAIN_RIM_Z in the MCU footprint X region.
    Actual outer +Y face at MCU X column is at Y≈116.5 (polygon-offset, not OUTER_DEPTH).
    """
    from build123d import Axis
    t = build_tray()
    high = (
        t.edges()
         .filter_by_position(Axis.Y, minimum=C.MCU_HILL_PLUS_Y_INNER_BOUND_Y, maximum=C.OUTER_DEPTH + 1.0)
         .filter_by_position(Axis.X, minimum=0.0, maximum=C.MCU_HILL_PLUS_Y_REACH_X + 1.0)
         .filter_by_position(Axis.Z, minimum=C.MAIN_RIM_Z + 1.0, maximum=999)
    )
    assert len(high) > 0, "+Y wall not raised in MCU region"


def test_tray_is_single_solid():
    """Hill must fuse with shell into one continuous solid — guards against the
    floating-slab regression where the hill cap was positioned outside the
    polygon-offset wall and rendered as a separate piece."""
    t = build_tray()
    assert len(t.solids()) == 1, f"tray has {len(t.solids())} solids; expected 1 fused solid"


def test_hill_outer_face_flush_with_shell():
    """The −X outer wall face at the MCU plateau must be ONE continuous face
    spanning from the floor up into the hill region — not a separate face
    starting above MAIN_RIM_Z. Proves shell and hill share the same offset wall."""
    t = build_tray()
    _, mcu_cy = C.pcb_to_case(*C.MCU_POS)

    # A flat −X face has X.min == X.max == polygon-offset X. Find faces at the
    # MCU column that span MCU_cy in Y and reach from below MAIN_RIM_Z up to
    # above (i.e., a single face spanning both shell and hill).
    spanning = []
    for f in t.faces():
        bb = f.bounding_box()
        if bb.max.X - bb.min.X > 0.01:
            continue   # not a flat −X-normal face
        if not (bb.min.Y < mcu_cy < bb.max.Y):
            continue
        if bb.min.X > 10:
            continue   # only −X (outer) wall side
        if bb.min.Z < C.MAIN_RIM_Z - 1.0 and bb.max.Z > C.MAIN_RIM_Z + 1.0:
            spanning.append(f)
    assert spanning, (
        "No −X outer face spans MAIN_RIM_Z at MCU Y — hill is built on a separate "
        "face from the shell (regression: floating slab)."
    )


def test_hill_plus_y_face_flush_with_shell():
    """+Y outer wall face at MCU X must be ONE continuous face spanning from
    floor through hill — guards against the original +Y slab placed at Y=121.5
    while the actual polygon-offset wall sits at Y≈116.5."""
    t = build_tray()
    mcu_cx, _ = C.pcb_to_case(*C.MCU_POS)

    spanning = []
    for f in t.faces():
        bb = f.bounding_box()
        if bb.max.Y - bb.min.Y > 0.01:
            continue   # not a flat +Y-normal face
        if not (bb.min.X < mcu_cx < bb.max.X):
            continue
        if bb.min.Y < C.MCU_HILL_PLUS_Y_INNER_BOUND_Y:
            continue   # only +Y outer side
        if bb.min.Z < C.MAIN_RIM_Z - 1.0 and bb.max.Z > C.MAIN_RIM_Z + 1.0:
            spanning.append(f)
    assert spanning, (
        "No +Y outer face spans MAIN_RIM_Z at MCU X — hill is on a separate face "
        "from the shell (regression: floating slab outboard of polygon offset)."
    )
