"""Flat bottom (no tent).

Replaces the old integrated-tent tests. The tent wedge, the seam wave/lens, the front/rear
skirts and the blind-port bottom skin were all removed: the case underside is a single planar
face at Z=0 and the two clamshell halves part along one flat Z=0 line. These tests pin exactly
that — the bottom is flat, level, and nothing dips below Z=0 — and that the internal Z-ladder
above the plate is untouched (both halves still compose to a single solid)."""
from sofle_case import constants as C
from sofle_case.case import ground_face, tent_ground_z, tent_plane, wedge_deep_z
from tests.shared_builds import build_bottom_part, build_top_part


def test_tent_constants_and_shims_are_flat():
    """The tent angle is zeroed and the ground helpers are flat Z=0 shims."""
    assert C.TENT_ANGLE_DEG == 0.0
    o, n = tent_plane()
    assert o == (0.0, 0.0, 0.0) and n == (0.0, 0.0, 1.0)
    for y in (0.0, 30.0, C.OUTER_DEPTH):
        assert tent_ground_z(y) == 0.0
    assert wedge_deep_z() == 0.0


def test_ground_face_is_one_flat_plane_at_z0():
    """A single planar down-face at Z=0, no pitch and no roll — the keyboard stands flat."""
    face = ground_face(build_bottom_part("right"))
    assert face is not None, "no ground face found"
    assert str(face.geom_type) == "GeomType.PLANE", f"ground face is {face.geom_type}"
    n = face.normal_at(face.center())
    assert abs(n.X) < 1e-9 and abs(n.Y) < 1e-9, f"ground face is not level: n={n}"
    assert abs(abs(n.Z) - 1.0) < 1e-9
    assert abs(face.center().Z) < 1e-6, f"ground face sits at Z={face.center().Z:.4f}, not 0"


def test_contact_is_the_whole_footprint():
    """The case rests on the full plan area of the flat underside, so it cannot rock."""
    face = ground_face(build_bottom_part("right"))
    assert face.area > 10000.0, f"ground face is only {face.area:.0f} mm²"


def test_nothing_pokes_below_z0():
    """Everything sits on or above Z=0; one stray vertex below becomes a rock point."""
    for side in ("right", "left"):
        verts, _f = build_bottom_part(side).tessellate(0.2)
        worst = min(v.Z for v in verts)
        assert worst > -1e-4, f"{side}: geometry dips {-worst:.4f} mm below Z=0"


def test_halves_are_single_solids_and_bottom_is_the_plate():
    """Both halves compose to one solid; the bottom is just the inset floor plate + standoffs
    (Z=0 up to the standoff tap tops, nothing tent-tall below Z=0), and the top carries the
    full stack well above the cover."""
    b = build_bottom_part("right")
    t = build_top_part("right")
    assert len(b.solids()) == 1, f"bottom is {len(b.solids())} solids"
    assert len(t.solids()) == 1, f"top is {len(t.solids())} solids"
    bb = b.bounding_box()
    assert abs(bb.min.Z) < 1e-6, f"bottom underside at Z={bb.min.Z:.4f}, not 0"
    assert bb.max.Z <= C.PLATE_SEAT_Z + 1e-3, f"bottom reaches Z={bb.max.Z:.4f}, above the plate seat"
    tb = t.bounding_box()
    assert abs(tb.min.Z) < 1e-3, f"top underside at Z={tb.min.Z:.4f}, not ~0"
    assert tb.max.Z > C.COVER_TOP_Z, "the canopy/encoder should rise above the cover top"
