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
