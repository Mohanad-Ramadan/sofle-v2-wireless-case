"""Flat bottom (no tent).

Replaces the old integrated-tent tests. The tent wedge, the seam wave/lens and the front/rear
skirts were removed: the two clamshell halves part along one flat Z=0 line. The blind-port bottom
SKIN is kept — it grows a thin cap down to Z=-(BSKIN_GAP + BSKIN_THICK) to hide the snap release
ports, so the underside the case stands on is that flat skin face, not Z=0. These tests pin that
the bottom is flat and level, nothing dips below the skin face, and the Z-ladder above the plate
is untouched (both halves still compose to a single solid)."""
from sofle_case import constants as C
from sofle_case.case import (ground_face, skin_ground_z, tent_ground_z, tent_plane,
                             wedge_deep_z, _skin_drop)
from tests.shared_builds import build_bottom_part, build_top_part

GROUND_Z = -( C.BSKIN_GAP + C.BSKIN_THICK )   # the blind-port skin's outer (desk) face


def test_tent_constants_and_shims_are_flat():
    """The tent angle is zeroed and the parting-plane helpers are flat Z=0 shims; the skin drops
    the true ground a gap+skin below that."""
    assert C.TENT_ANGLE_DEG == 0.0
    o, n = tent_plane()
    assert o == (0.0, 0.0, 0.0) and n == (0.0, 0.0, 1.0)
    for y in (0.0, 30.0, C.OUTER_DEPTH):
        assert tent_ground_z(y) == 0.0
        assert abs(skin_ground_z(y) - GROUND_Z) < 1e-9
    assert wedge_deep_z() == 0.0
    assert abs(_skin_drop() - (C.BSKIN_GAP + C.BSKIN_THICK)) < 1e-9


def test_ground_face_is_one_flat_plane():
    """A single planar down-face at the skin ground, no pitch and no roll — the keyboard stands
    flat on the blind-port skin."""
    face = ground_face(build_bottom_part("right"))
    assert face is not None, "no ground face found"
    assert str(face.geom_type) == "GeomType.PLANE", f"ground face is {face.geom_type}"
    n = face.normal_at(face.center())
    assert abs(n.X) < 1e-9 and abs(n.Y) < 1e-9, f"ground face is not level: n={n}"
    assert abs(abs(n.Z) - 1.0) < 1e-9
    assert abs(face.center().Z - GROUND_Z) < 1e-6, \
        f"ground face sits at Z={face.center().Z:.4f}, not the skin ground {GROUND_Z}"


def test_contact_is_the_whole_footprint():
    """The case rests on the full plan area of the flat skin underside, so it cannot rock."""
    face = ground_face(build_bottom_part("right"))
    assert face.area > 10000.0, f"ground face is only {face.area:.0f} mm²"


def test_nothing_pokes_below_the_skin_ground():
    """Everything sits on or above the skin ground; one stray vertex below becomes a rock point."""
    for side in ("right", "left"):
        verts, _f = build_bottom_part(side).tessellate(0.2)
        worst = min(v.Z for v in verts)
        assert worst > GROUND_Z - 1e-4, f"{side}: geometry dips {GROUND_Z - worst:.4f} mm below the skin"


def test_halves_are_single_solids_and_bottom_is_the_plate():
    """Both halves compose to one solid; the bottom is the inset floor plate + standoffs + the
    blind-port skin (skin ground up to the standoff tap tops), and the top carries the full stack
    well above the cover."""
    b = build_bottom_part("right")
    t = build_top_part("right")
    assert len(b.solids()) == 1, f"bottom is {len(b.solids())} solids"
    assert len(t.solids()) == 1, f"top is {len(t.solids())} solids"
    bb = b.bounding_box()
    assert abs(bb.min.Z - GROUND_Z) < 1e-6, f"bottom underside at Z={bb.min.Z:.4f}, not the skin ground"
    assert bb.max.Z <= C.PLATE_SEAT_Z + 1e-3, f"bottom reaches Z={bb.max.Z:.4f}, above the plate seat"
    tb = t.bounding_box()
    # the top's outer skirt descends to hide the bottom skin, its lower edge cut to the S-spline
    # lens; the front pinch (SEAM_LENS_FRONT_Z) is the lowest the top reaches (rear is raised)
    assert abs(tb.min.Z - min(C.SEAM_LENS_FRONT_Z, C.SEAM_LENS_REAR_Z)) < 1e-3, \
        f"top skirt at Z={tb.min.Z:.4f}, not the lens front pinch"
    assert tb.max.Z > C.COVER_TOP_Z, "the canopy/encoder should rise above the cover top"
