"""Tests for the drafted rim facet: a wedge shaved from the outer-wall top all round
(RIM_FACET_*), with a deeper, more aggressive facet on the palm-facing south run
(FRONT_FACET_*). The +Y relief bump is excluded so it keeps its square top edge."""
import math
from collections import defaultdict

from build123d import Solid
from sofle_case import constants as C
from tests.shared_builds import build_tray

# Nominal |normal.Z| of each drafted plane: run / hypot(run, drop).
NZ_PERIM = C.RIM_FACET_RUN / math.hypot(C.RIM_FACET_RUN, C.RIM_FACET_DROP)
NZ_FRONT = C.FRONT_FACET_RUN / math.hypot(C.FRONT_FACET_RUN, C.FRONT_FACET_DROP)


def _solid_at(part, x: float, y: float, z: float, s: float = 0.3) -> bool:
    probe = Solid.make_box(s, s, s).translate((x - s / 2, y - s / 2, z - s / 2))
    return (part & probe).volume > 1e-6


def _facet_faces(part, rim_z: float):
    """Every sloped face in the facet band — i.e. the chamfer itself, excluding the
    vertical walls (|nz|~0) and the horizontal rim/floor (|nz|~1)."""
    band_lo = rim_z - C.FRONT_FACET_DROP - 0.05
    out = []
    for f in part.faces():
        bb = f.bounding_box()
        if bb.max.Z < band_lo or bb.min.Z > rim_z + 0.05:
            continue
        nz = f.normal_at(f.center()).Z
        if 0.02 < abs(nz) < 0.995:
            out.append((f, bb, abs(nz)))
    return out


def test_tray_single_solid_with_facets():
    """The two facet cutters must not fracture the shell into multiple solids."""
    for rim in (C.MAIN_RIM_Z, C.COVER_TOP_Z):
        t = build_tray(rim_z=rim)
        assert len(t.solids()) == 1, f"rim={rim}: {len(t.solids())} solids, expected 1"


def test_constants_guards_hold():
    """The facet must leave >=1.5 mm rim wall, clear the membrane fuse band, and keep its
    south toe above the rabbet skin zone (these are asserted at import too — restated here)."""
    assert C.FRONT_FACET_RUN <= C.WALL_THICKNESS - 1.5
    assert C.RIM_FACET_RUN <= C.WALL_THICKNESS - 1.5
    assert C.FRONT_FACET_RUN < C.WALL_THICKNESS - C.COVER_FUSE_MARGIN
    assert C.COVER_TOP_Z - C.FRONT_FACET_DROP >= C.SEAM_LEDGE_Z + 1.0


def test_south_facet_removes_front_top():
    """South front outer-top is cut (air at the rim); full wall remains below the toe."""
    t = build_tray(rim_z=C.COVER_TOP_Z)
    x = 80.0                      # mid front span (inner edge y=23.2 -> outer face ~y=18)
    assert not _solid_at(t, x, 18.5, C.COVER_TOP_Z - 0.5), "south facet did not cut the rim"
    assert _solid_at(t, x, 18.5, C.COVER_TOP_Z - C.FRONT_FACET_DROP - 1.0), \
        "south wall should be solid below the facet toe"


def test_perimeter_facet_removes_side_top():
    """East outer-top sliver is cut near the rim; solid remains below the perimeter toe."""
    t = build_tray(rim_z=C.COVER_TOP_Z)
    x = C.OUTER_WIDTH - 0.5       # in the outer 2 mm the perimeter facet removes
    assert not _solid_at(t, x, 60.0, C.COVER_TOP_Z - 0.4), "perimeter facet did not cut the side rim"
    assert _solid_at(t, x, 60.0, C.COVER_TOP_Z - C.RIM_FACET_DROP - 1.0), \
        "side wall should be solid below the perimeter facet toe"


def test_south_mask_two_clean_slashes():
    """Deep facet covers the low front (thumb ramp -> flat -> E4). The East '\\' is the cap
    y=FRONT_FACET_Y_MASK crossing E4; the West '/' is a DERIVED exact mirror twin of it — same X-run,
    centred at the thumb-switch midpoint, leaning the mirror way. Thumb tip + side/back walls shallow."""
    from build123d import Solid
    from sofle_case.tray import _front_facet_mask, _front_slash_crossings, _poly_pts, _outer_poly_pts
    from sofle_case.pcb_geometry import thumb_switch_midpoint_x
    # the SW ramp is straightened for the outer wall / facet only (kink pts[3] dropped)
    assert len(_outer_poly_pts()) == len(_poly_pts()) - 1

    east_rim, east_toe, west_rim, west_toe = _front_slash_crossings()
    east_run = east_toe[0] - east_rim[0]                 # East '\': rim->toe, +east
    west_run = west_rim[0] - west_toe[0]                 # West '/': rim east of toe
    assert west_run > 0, "West must lean '/' (rim east of toe)"
    assert abs(west_run - abs(east_run)) < 0.3, "West run must match the East — exact twins"
    assert abs((west_rim[0] + west_toe[0]) / 2 - thumb_switch_midpoint_x()) < 0.2, \
        "West must be centred at the thumb-switch midpoint"
    assert abs(east_rim[0] - 122.44) < 0.5 and abs(east_toe[0] - 134.23) < 0.5, \
        "East slash moved off its original E4 place"

    m = _front_facet_mask()

    def inside(x, y, z=8.0):  # the mask is a plan prism, so z only has to sit inside its extent
        return (m & Solid.make_box(0.3, 0.3, 0.3).translate((x - 0.15, y - 0.15, z - 0.15))).volume > 1e-6

    # deep just east of the West crease, shallow just west (toward the thumb tip), probed at mid-height
    ymid = (west_toe[1] + west_rim[1]) / 2
    wx_mid = west_toe[0] + (west_rim[0] - west_toe[0]) * (ymid - west_toe[1]) / (west_rim[1] - west_toe[1])
    assert inside(wx_mid + 1.5, ymid), "deep facet missing east of the West cut"
    assert not inside(wx_mid - 1.5, ymid), "deep leaked toward the thumb tip"

    # flat + E4 deep; north of the cap + far west wall shallow
    assert inside(80.0, 20.0), "central flat front should be deep"
    assert inside(115.0, 22.0), "E4 near the flat-front corner should be deep"
    assert not inside(80.0, C.FRONT_FACET_Y_MASK + 2.0), "north of the cap should be shallow"
    assert not inside(12.0, 20.0), "west wall should stay shallow"


def test_west_rim_facet_continuous_across_bump_handover():
    """No bare strip where the polygon facet hands over to the bump's own west wedge.

    The exclusion box and the replacement wedge used to disagree by 0.15 mm, leaving a strip of
    full-thickness wall standing 2 mm proud of the facet — a 4 mm tall razor fin at the rim."""
    t = build_tray(rim_z=C.COVER_TOP_Z)
    x_out = C.pcb_to_case(0, 0)[0] - C.WALL_THICKNESS - C.PCB_XY_CLEARANCE   # 8.5
    for y in (114.6, 114.9, 115.0, 115.05, 115.1, 115.2, 115.5, 116.0):
        assert not _solid_at(t, x_out + 0.3, y, C.COVER_TOP_Z - 0.4, s=0.1), \
            f"un-faceted fin left standing on the west rim at y={y}"


def test_facet_is_exact_planes_and_cones():
    """Every chamfer face is an exact PLANE or CONE at one of the two nominal draft
    angles — no approximating spline patches, no sliver faces.

    Regression guard. The facet used to be a loft between two Kind.ARC offsets of the
    same wire, but an outward arc-offset does not preserve edge count: the sections
    came out 23 vs 24 edges (perimeter) and 23 vs 27 (front). With no 1:1 vertex
    correspondence OCC abandoned ruled surfaces and approximated the whole band with
    BSpline patches — the draft angle wandered by up to |Δnz| = 0.45 and the chamfer
    width by millimetres at the outline corners, which read as kinks and surface noise
    on the printed rim. A drafted prism has no such failure mode.
    """
    rim = C.COVER_TOP_Z
    faces = _facet_faces(build_tray(rim_z=rim), rim)
    assert faces, "no facet faces found"

    bad_type = [f for f, _, _ in faces
                if str(f.geom_type) not in ("GeomType.PLANE", "GeomType.CONE")]
    assert not bad_type, (
        "facet must be exact planes/cones, got "
        f"{[(str(f.geom_type), round(f.area, 2)) for f in bad_type]}"
    )

    off = [(round(nz, 4), round(f.area, 3), tuple(round(v, 1) for v in f.center()))
           for f, _, nz in faces
           if min(abs(nz - NZ_PERIM), abs(nz - NZ_FRONT)) > 1e-6]
    assert not off, f"facet faces off the nominal draft angle: {off}"

    slivers = [(round(f.area, 5), tuple(round(v, 1) for v in f.center()))
               for f, _, _ in faces if f.area < 1.0]
    assert not slivers, f"sliver facet faces (surface noise): {slivers}"


def test_facet_toe_sits_exactly_at_its_nominal_z():
    """Each chamfer face starts exactly at rim − DROP. A toe that wanders in Z is a
    visible waver in the line where the chamfer meets the wall."""
    rim = C.COVER_TOP_Z
    for f, bb, nz in _facet_faces(build_tray(rim_z=rim), rim):
        drop = C.RIM_FACET_DROP if abs(nz - NZ_PERIM) < 1e-6 else C.FRONT_FACET_DROP
        assert abs(bb.min.Z - (rim - drop)) < 1e-6, (
            f"facet toe at Z={bb.min.Z:.4f}, expected {rim - drop:.4f} "
            f"(face at {tuple(round(v, 1) for v in f.center())})"
        )


def test_facet_ring_is_tangent_continuous():
    """Neighbouring chamfer faces meet tangentially all the way round, so the drafted
    band reads as one continuous surface instead of a chain of mitred segments.

    The intentional SW/SE front creases are NOT part of this: they are the boundary
    between the perimeter facet and the deeper front facet, which meet along the mask
    edge rather than sharing an edge between two faces of this band."""
    rim = C.COVER_TOP_Z
    faces = _facet_faces(build_tray(rim_z=rim), rim)
    shared = defaultdict(list)
    for i, (f, _, _) in enumerate(faces):
        for e in f.edges():
            a, b = e.position_at(0), e.position_at(1)
            key = tuple(round(v, 3) for v in (a.X, a.Y, a.Z, b.X, b.Y, b.Z))
            shared[min(key, key[3:] + key[:3])].append((i, e))

    kinks = []
    for pair in shared.values():
        if len(pair) != 2:
            continue
        (i, e), (j, _) = pair
        if i == j:
            continue
        m = e.position_at(0.5)
        dot = faces[i][0].normal_at(m).dot(faces[j][0].normal_at(m))
        angle = math.degrees(math.acos(max(-1.0, min(1.0, dot))))
        if angle >= 0.5:
            kinks.append((round(angle, 2), tuple(round(v, 1) for v in m)))
    assert not kinks, f"non-tangent joints in the facet ring: {kinks}"


def test_bump_face_carries_facet():
    """The +Y relief bump's proud face carries the SAME drafted chamfer as every other wall
    (via its own face-aligned wedges) — no bare square stretch on the north wall."""
    t = build_tray(rim_z=C.COVER_TOP_Z)
    y_out = C.pcb_to_case(0, C.MCU_Y_RELIEF_TARGET_Y)[1] + C.WALL_THICKNESS + C.PCB_XY_CLEARANCE
    # near-rim outer sliver of the bump face is shaved away by the wedge
    assert not _solid_at(t, 30.0, y_out - 0.3, C.COVER_TOP_Z - 0.4), \
        "bump face not chamfered at the rim"
    # below the facet toe the bump face is still full
    assert _solid_at(t, 30.0, y_out - 0.3, C.COVER_TOP_Z - C.RIM_FACET_DROP - 1.0), \
        "bump face missing below the chamfer toe"
