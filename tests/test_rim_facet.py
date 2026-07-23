"""Tests for the drafted rim facet: a wedge shaved from the outer-wall top all round
(RIM_FACET_*), with a deeper, more aggressive facet on the palm-facing south run
(FRONT_FACET_*). The +Y relief bump is excluded so it keeps its square top edge."""
from build123d import Solid
from sofle_case import constants as C
from sofle_case.tray import build_tray


def _solid_at(part, x: float, y: float, z: float, s: float = 0.3) -> bool:
    probe = Solid.make_box(s, s, s).translate((x - s / 2, y - s / 2, z - s / 2))
    return (part & probe).volume > 1e-6


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
    """The deep facet spans the low central front (E4 flat + flanking ramps), held between two
    clean slashes: the SE slash (flat cap crossing E5) and the SW slash (a vertical cut across
    the single straight E3 ramp at FRONT_FACET_SW_X). West of the SW cut — E2, thumb wall, west
    wall — is plain shallow. One wall style, exactly two creases; near-mirror matched pair."""
    from build123d import Solid
    from sofle_case.tray import _front_facet_mask, _poly_pts
    m = _front_facet_mask()

    def inside(x, y, z=8.0):
        return (m & Solid.make_box(0.3, 0.3, 0.3).translate((x - 0.15, y - 0.15, z - 0.15))).volume > 1e-6

    xw = C.FRONT_FACET_SW_X
    # SW slash is a clean vertical cut across E3: deep just east, shallow just west, same y.
    assert inside(xw + 1.5, 18.0), "deep facet missing just east of the SW cut"
    assert not inside(xw - 1.5, 18.0), "deep facet leaked west of the SW cut"
    # thumb wall + west stay shallow (no deep facet, no extra crease)
    pts = _poly_pts()
    v1, v2 = pts[1], pts[2]                 # thumb wall E1
    assert not inside((v1[0] + v2[0]) / 2, (v1[1] + v2[1]) / 2), "thumb wall still deep-faceted"
    # central flat front deep; side/back (north of the cap) shallow
    assert inside(80.0, 20.0)
    assert not inside(80.0, C.FRONT_FACET_Y_MASK + 2.0)


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
