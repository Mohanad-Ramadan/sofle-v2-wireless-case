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
    """The deep facet is confined to the flat central panel, held between two OBLIQUE slashes
    that are exact mirror images about the panel centre. The thumb ramps E2/E3, the SE ramp E4
    and the side/back walls are plain shallow — exactly two creases, a true mirror pair."""
    from build123d import Solid
    from sofle_case.tray import (
        _front_facet_mask, _front_slash_crossings, _front_panel_params, _poly_pts,
    )
    m = _front_facet_mask()
    axis, _y_toe, _slope, _ht = _front_panel_params()

    def inside(x, y, z=8.0):  # the mask is a plan prism, so z only has to be inside its extent
        return (m & Solid.make_box(0.3, 0.3, 0.3).translate((x - 0.15, y - 0.15, z - 0.15))).volume > 1e-6

    # exact mirror symmetry about the flat-panel centre — the core requirement
    for x, y in [(70.0, 19.0), (60.0, 18.0), (75.0, 20.0), (50.0, 18.0)]:
        assert inside(x, y) == inside(2 * axis - x, y), f"mask not mirror-symmetric at ({x}, {y})"

    west_rim, west_toe, east_rim, east_toe = _front_slash_crossings()
    # each slash is oblique: deep just inside the toe crossing, shallow just outside it
    assert inside(west_toe[0] + 1.5, west_toe[1]), "deep facet missing just inside the west toe"
    assert not inside(west_toe[0] - 1.5, west_toe[1]), "deep facet leaked west of the west slash"
    assert inside(east_toe[0] - 1.5, east_toe[1]), "deep facet missing just inside the east toe"
    assert not inside(east_toe[0] + 1.5, east_toe[1]), "deep facet leaked east of the east slash"
    # the slash leans in: at the rim y the panel is narrower, so the toe's x is now outside
    assert inside(west_rim[0] + 1.5, west_rim[1]), "deep facet missing just inside the west rim"
    assert not inside(west_toe[0], west_rim[1]), "rim panel should be narrower than the toe (slash not leaning)"

    pts = _poly_pts()
    v1, v2 = pts[1], pts[2]                 # thumb wall
    assert not inside((v1[0] + v2[0]) / 2, (v1[1] + v2[1]) / 2), "thumb wall still deep-faceted"
    # the flanking ramps are now plain shallow (deep facet confined to the flat panel)
    assert not inside(45.0, 17.0), "E3 ramp should be shallow now"
    assert not inside(120.0, 20.0), "E4 ramp should be shallow now"
    # central flat front deep; north of the apex shallow
    assert inside(80.0, 20.0)
    assert not inside(80.0, 26.0)


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
