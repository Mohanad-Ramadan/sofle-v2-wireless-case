"""Tests for the fastback canopy — now FUSED into the TOP cover.

The canopy's ramp merges tangentially DOWN into the cover surface (no tongue) and
``build_top_part`` adds it onto the TOP, so the MCU hood is integral to the cover. Parameters
live on the canopy module (``CAN.CANOPY_*``). South→north: the ramp foot merges into the cover
→ a tangent S-curve slip → flat roof at the ridge → short round-over + vertical north wall with
the USB-C port; N/W walls land at the chamfer FIRST point, NW corner rounded to the case radius.
"""
import pytest
from build123d import Solid, GeomType
from OCP.BRepCheck import BRepCheck_Analyzer

from sofle_case import constants as C
from sofle_case import canopy as CAN
from sofle_case.canopy import build_canopy
from sofle_case.case import build_top_part
from sofle_case.pcb_phantom import build_pcb_phantom


def _mcu_cx() -> float:
    return C.pcb_to_case(*C.MCU_POS)[0]


def _roof_top(part, x, y, sx=0.3, sy=0.3):
    col = Solid.make_box(sx, sy, 40).translate((x - sx / 2, y - sy / 2, 0))
    inter = part & col
    s = [] if inter is None else list(inter.solids())
    return max(ss.bounding_box().max.Z for ss in s) if s else None


def _solid_at(part, x, y, z, s=0.3):
    box = Solid.make_box(s, s, s).translate((x - s / 2, y - s / 2, z - s / 2))
    inter = part & box
    return inter is not None and sum(ss.volume for ss in inter.solids()) > 1e-6


def _curved_faces(part):
    return [f for f in part.faces() if f.geom_type != GeomType.PLANE]


@pytest.mark.parametrize("hollow", [False, True])
def test_canopy_is_valid_single_solid(hollow):
    c = build_canopy(hollow=hollow)
    assert len(c.solids()) == 1
    assert BRepCheck_Analyzer(c.wrapped).IsValid()


def test_canopy_foot_merges_into_cover_no_tongue():
    """The ramp foot merges tangentially into the cover surface — the roofline is AT the cover
    top at the foot (not a raised tongue), and it stays near the cover just north of the foot
    (horizontal tangent), then climbs."""
    c = build_canopy()
    assert abs(c.bounding_box().min.Y - CAN.CANOPY_RAMP_FOOT_Y) < 0.05, "canopy extends south of the foot"
    z_foot = _roof_top(c, _mcu_cx(), CAN.CANOPY_RAMP_FOOT_Y + 0.3)
    assert z_foot is not None and abs(z_foot - CAN.CANOPY_FOOT_Z) < 0.3, f"foot not at cover: {z_foot}"
    # tangent-flat at the foot: only just above the cover a little way north (no standing slab)
    z_near = _roof_top(c, _mcu_cx(), CAN.CANOPY_RAMP_FOOT_Y + 1.5)
    assert z_near is not None and z_near < CAN.CANOPY_FOOT_Z + 0.6, f"foot not tangent (steps up): {z_near}"


def test_canopy_closes_strip_in_front_of_plateau():
    """Regression guard: the ramp foot must land ON the encoder plateau's north face so the bay
    strip in front of the plateau is closed. This 'tongue gap' reopened once when the canopy was
    fused into the TOP; keep the foot south of the plateau north edge (with overlap)."""
    c = build_canopy()
    plateau_north = C.pcb_to_case(*C.SW_ENCODER_POS)[1] + CAN.CANOPY_ENCODER_HALF
    assert c.bounding_box().min.Y <= plateau_north + 1e-6, (
        f"canopy south {c.bounding_box().min.Y:.2f} leaves a strip north of the plateau "
        f"({plateau_north:.2f}) — the hole in front of the plateau is back"
    )


def test_canopy_west_shoulder_rounded_east_left_sharp():
    """The tall west + NW top shoulder is rounded (case style); the east top edge stays sharp."""
    c = build_canopy()
    xw, xe = CAN.CANOPY_WEST_OUTER_X, CAN.CANOPY_EAST_X
    west = [f for f in _curved_faces(c) if abs(f.center().X - xw) < 3.5
            and f.center().Z > C.COVER_TOP_Z + 2]
    east_top = [f for f in _curved_faces(c) if abs(f.center().X - xe) < 2.0
                and f.center().Z > C.COVER_TOP_Z + 2 and f.center().Y > CAN.CANOPY_RAMP_TOP_Y]
    assert west, "west top shoulder is not rounded"
    assert not east_top, "east top edge should stay sharp"


def test_canopy_ramp_is_smooth_and_tangent():
    """The ramp climbs monotonically from the cover to the ridge, is a real curved (Spline)
    surface (no facet steps), and is tangent at BOTH ends (S-curve)."""
    c = build_canopy()
    foot, top = CAN.CANOPY_RAMP_FOOT_Y, CAN.CANOPY_RAMP_TOP_Y
    zs = [_roof_top(c, _mcu_cx(), foot + t * (top - foot)) for t in (0.0, 0.25, 0.5, 0.75, 1.0)]
    assert all(z is not None for z in zs)
    assert all(b >= a - 1e-6 for a, b in zip(zs, zs[1:])), f"ramp not monotonic: {zs}"
    assert abs(zs[0] - CAN.CANOPY_FOOT_Z) < 0.3 and abs(zs[-1] - CAN.CANOPY_RIDGE_TOP_Z) < 0.2
    ramp_curved = [f for f in _curved_faces(c)
                   if foot < f.center().Y < top and C.COVER_TOP_Z < f.center().Z < CAN.CANOPY_RIDGE_TOP_Z]
    assert ramp_curved, "ramp has no smooth curved face (faceted?)"


def test_canopy_flat_roof_at_ridge():
    c = build_canopy()
    for y in (90.0, 105.0, 113.0):
        z = _roof_top(c, _mcu_cx(), y)
        assert z is not None and abs(z - CAN.CANOPY_RIDGE_TOP_Z) < 0.05, f"roof not flat at y={y}: {z}"


def test_canopy_ridge_is_tallest_point():
    c = build_canopy()
    assert abs(c.bounding_box().max.Z - CAN.CANOPY_RIDGE_TOP_Z) < 0.01


def test_canopy_walls_at_chamfer_first_point():
    """N/W walls land at the chamfer first point; east on the switch-column boundary."""
    c = build_canopy()
    bb = c.bounding_box()
    assert abs(bb.min.X - CAN.CANOPY_WEST_OUTER_X) < 0.05
    assert abs(bb.max.Y - CAN.CANOPY_NORTH_OUTER_Y) < 0.05
    assert abs(bb.max.X - CAN.CANOPY_EAST_X) < 0.05


def test_canopy_nw_corner_is_rounded():
    """The NW corner is rounded to the case's corner radius (sharp corner cut back)."""
    c = build_canopy()
    xw, yn, r = CAN.CANOPY_WEST_OUTER_X, CAN.CANOPY_NORTH_OUTER_Y, CAN.CANOPY_CORNER_R
    assert not _solid_at(c, xw + 0.3, yn - 0.3, 16.0), "NW corner is sharp, not rounded"
    assert _solid_at(c, xw + 0.3, 100.0, 16.0), "west wall missing away from the corner"
    assert [f for f in _curved_faces(c) if f.center().X < xw + r and f.center().Y > yn - r]


def test_canopy_is_hollow_shell():
    c = build_canopy()
    assert not _solid_at(c, _mcu_cx(), 100.0, CAN.CANOPY_RIDGE_TOP_Z - CAN.CANOPY_ROOF_WALL - 1.0), \
        "canopy is not hollow under the roof"
    assert build_canopy().volume < build_canopy(hollow=False).volume


def test_reset_poke_hole_open():
    """A vertical poke bore pierces the canopy roof directly above RSW1, the roof stays solid
    just beside it, and the countersunk funnel widens the mouth at the surface."""
    c = build_canopy()
    rx, ry = C.pcb_to_case(*C.SW_RESET_POS)
    surf_z = CAN._canopy_roof_z(ry)
    z_in_roof = surf_z - 0.75                      # inside the roof shell, on the bore axis
    assert not _solid_at(c, rx, ry, z_in_roof), "reset poke bore is blocked"
    beside = CAN.RESET_POKE_DIA / 2 + 1.5
    assert _solid_at(c, rx + beside, ry, z_in_roof), "roof missing beside the poke bore"
    # Funnel: material is removed out to near the mouth radius just below the surface,
    # wider than the plain bore would reach.
    mouth = CAN.RESET_FUNNEL_MOUTH_DIA / 2
    assert not _solid_at(c, rx + mouth - 0.7, ry, surf_z - 0.2), "funnel mouth not widened"


@pytest.mark.parametrize("side", ["right", "left"])
def test_reset_poke_hole_open_in_fused_top(side):
    """The poke-hole survives fusion into the TOP part (not backfilled by cover/walls)."""
    top = build_top_part(side)
    rx, ry = C.pcb_to_case(*C.SW_RESET_POS)
    if side == "left":
        rx = C.OUTER_WIDTH - rx
    surf_z = CAN._canopy_roof_z(ry)
    assert not _solid_at(top, rx, ry, surf_z - 0.75), f"{side} TOP reset bore blocked"


def test_canopy_usb_port_open():
    """A USB-C hole is cut through the north wall on the MCU X column; the wall stays solid to
    either side of it."""
    c = build_canopy()
    ncx = _mcu_cx()
    yw = CAN.CANOPY_NORTH_OUTER_Y - CAN.CANOPY_SIDE_WALL / 2
    assert not _solid_at(c, ncx, yw, 16.0), "USB port blocked"
    assert _solid_at(c, ncx + CAN.CANOPY_USB_W / 2 + 1.5, yw, 15.0), "north wall missing beside the port"


# ---------------------------------------------------------------------------
# Fused into the TOP
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("side", ["right", "left"])
def test_canopy_fused_into_top_single_solid(side):
    top = build_top_part(side)
    assert top.is_valid and len(top.solids()) == 1, f"{side} TOP not one valid solid"
    assert abs(top.bounding_box().max.Z - CAN.CANOPY_RIDGE_TOP_Z) < 0.01, "TOP not raised to the canopy ridge"


def test_fused_top_clears_all_bay_components():
    """The fused TOP (cover + canopy) must not touch any component above the cover."""
    top = build_top_part("right")
    above = Solid.make_box(200, 200, 60).translate((-20, -20, C.COVER_TOP_Z + 0.1))
    clash = (top & build_pcb_phantom()) & above
    vol = 0.0 if clash is None else sum(s.volume for s in clash.solids())
    assert vol < 1e-2, f"canopy clashes bay components by {vol:.2f} mm^3"
