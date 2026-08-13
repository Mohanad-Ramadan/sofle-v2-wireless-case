"""Tests for the fastback canopy — now FUSED into the TOP cover.

The canopy's ramp merges tangentially DOWN into the cover surface (no tongue) and
``build_top_part`` adds it onto the TOP, so the MCU hood is integral to the cover. Parameters
live on the canopy module (``CAN.CANOPY_*``). South→north: the ramp foot merges into the cover
→ a tangent S-curve slip → flat roof at the ridge → short round-over + vertical north wall with
the USB-C port; N/W walls land at the chamfer FIRST point, NW corner rounded to the case radius.
The west top shoulder's drafted facet is cut by a swept boolean, not a 3-D edge chamfer, so it
survives the ramp spline's control-point density. The ridge is derived per half, not shared,
since the two halves' ports sit at different Z.
"""
import pytest
from build123d import Solid, GeomType
from OCP.BRepCheck import BRepCheck_Analyzer

from sofle_case import constants as C
from sofle_case import canopy as CAN
from tests.shared_builds import build_canopy
from tests.shared_builds import build_top_part
from sofle_case.pcb_phantom import build_pcb_phantom
from sofle_case.encoder_phantom import build_encoder_phantom


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


def _mirror_back(part):
    """Undo build_top_part's left-half mirror, so a left TOP can be compared against the
    phantoms — which are always built in right-half (un-mirrored) coordinates."""
    from build123d import Plane, Pos, mirror
    p = Pos(-C.OUTER_WIDTH / 2, 0, 0) * part
    p = mirror(p, about=Plane.YZ)
    return Pos(C.OUTER_WIDTH / 2, 0, 0) * p


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


@pytest.mark.parametrize("side", ["right", "left"])
def test_canopy_west_top_facet_runs_the_whole_shoulder(side):
    """The west top shoulder carries its drafted facet along the WHOLE run — ramp and flat roof
    — while the east top edge stays sharp.

    This is the regression that ``_round_west_top_edges`` used to lose SILENTLY: its 3-D
    ``chamfer()`` (and every fallback) is rejected by OCC once the ramp Spline is interpolated
    through more than ~9 control points, and it returned the part untouched rather than raising.
    Measured: the facet landed at CANOPY_RAMP_SAMPLES = 9 and at NO value from 13 up, so raising
    the sample count to damp the ramp's ringing silently deleted the facet. ``_chamfer_west_top``
    is a swept boolean instead, so it is independent of sample count — probe the run at several
    stations, not just one, because a partial cut is the plausible failure now."""
    # puzzle=False: the subject here is the shoulder facet and the SHARP east arris. The roof's
    # puzzle strokes end in rounded caps, and the east-most cap's face centre lands inside this
    # test's 2.0 mm window on the arris — so a groove terminal sitting 2.4 mm inboard would be read
    # as a rounded east edge. That the strokes never actually touch the arris is asserted by
    # test_canopy_puzzle.py::test_the_east_arris_is_not_broken.
    c = build_canopy(side=side, puzzle=False)
    xw, xe = CAN.CANOPY_WEST_OUTER_X, CAN.CANOPY_EAST_X
    z_ridge = CAN.canopy_ridge_top_z(side)
    # Stations spanning the ramp's upper half and the flat roof (the foot is excluded on
    # purpose: the facet fades out there, where the west wall is only 1 mm tall).
    for y in (70.8, 76.8, 82.8, 94.8, 106.8, 112.8):
        rz = CAN._canopy_roof_z(y, z_ridge)
        assert not _solid_at(c, xw + 0.35, y, rz - 0.35, s=0.2), \
            f"{side}: west top shoulder is sharp at Y={y} (facet missing or partial)"
        assert _solid_at(c, xw + 0.35, y, rz - 3.2, s=0.2), \
            f"{side}: west wall gone below the facet at Y={y} (cut too deep)"
    # The fuse overlap under the ramp foot must survive the facet's lead-in.
    assert _solid_at(c, xw + 0.4, 60.0, 15.4), "facet ate the fuse overlap at the ramp foot"
    east_top = [f for f in _curved_faces(c) if abs(f.center().X - xe) < 2.0
                and f.center().Z > C.COVER_TOP_Z + 2 and f.center().Y > CAN.CANOPY_RAMP_TOP_Y]
    assert not east_top, "east top edge should stay sharp"


def test_canopy_ramp_mesh_does_not_detonate():
    """The ramp spline must stay cheap to TESSELLATE, not just accurate.

    OCC meshes by curvature (angular tolerance), not by deviation, and a denser interpolating
    spline trades deviation for high-frequency curvature wiggle. Raising CANOPY_RAMP_SAMPLES to
    51 cut the ramp's deviation to 0.0086 mm — invisible under a 0.2 mm layer — and took the
    right half's TOP from 50k to 797k triangles (a 2.5 MB STL to 39.9 MB). Nothing caught it:
    every geometric assertion passed, because the SHAPE was fine and only the mesh was absurd.

    The right half is the one that blows up (its ramp is 2.76 mm taller, so its curvature is
    worse), so probe it. The bound is deliberately loose — this guards against the order-of-
    magnitude cliff past ~25 samples, not against normal drift."""
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.BRep import BRep_Tool
    from OCP.TopLoc import TopLoc_Location

    c = build_canopy(side="right")
    BRepMesh_IncrementalMesh(c.wrapped, 1e-3, False, 0.1, True)
    n = 0
    for f in c.faces():
        tri = BRep_Tool.Triangulation_s(f.wrapped, TopLoc_Location())
        n += tri.NbTriangles() if tri is not None else 0
    assert n < 150_000, (
        f"canopy meshes to {n} triangles — the ramp spline's curvature has detonated. "
        f"CANOPY_RAMP_SAMPLES is {CAN.CANOPY_RAMP_SAMPLES}; it is a CEILING, see its comment."
    )


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


@pytest.mark.parametrize("side", ["right", "left"])
def test_canopy_nw_corner_is_rounded(side):
    """The NW corner is ROUNDED to the case's corner radius (sharp corner cut back), and cleanly
    so — exactly one CYLINDER face, no kink patches.

    The corner was briefly a flat diagonal chamfer, to escape a measured 64.7° kink (OCC
    auto-inserting CONE/BSPLINE patches at the seam where the cylinder met the sloped north-top
    chamfer). That kink was real but misattributed: it was measured while the west top shoulder's
    facet was silently missing, so the cylinder ran into a raw square shoulder. With the facet
    actually cut (``_chamfer_west_top``), the corner resolves to a single clean cylindrical face —
    which is what the geom_type assertion below pins, so a regression to the kink fails loudly."""
    c = build_canopy(side=side)
    xw, yn, r = CAN.CANOPY_WEST_OUTER_X, CAN.CANOPY_NORTH_OUTER_Y, CAN.CANOPY_CORNER_R
    assert not _solid_at(c, xw + 0.3, yn - 0.3, 16.0), "NW corner is sharp, not rounded"
    assert _solid_at(c, xw + 0.3, 100.0, 16.0), "west wall missing away from the corner"
    corner_faces = [f for f in c.faces() if f.center().X < xw + r and f.center().Y > yn - r]
    kinds = sorted({str(f.geom_type).split(".")[-1] for f in corner_faces})
    assert kinds == ["CYLINDER"], \
        f"NW corner should be one clean round, found {kinds} ({len(corner_faces)} faces)"


def test_canopy_is_hollow_shell():
    c = build_canopy()
    assert not _solid_at(c, _mcu_cx(), 100.0, CAN.CANOPY_RIDGE_TOP_Z - CAN.CANOPY_ROOF_WALL - 1.0), \
        "canopy is not hollow under the roof"
    assert build_canopy().volume < build_canopy(hollow=False).volume


@pytest.mark.parametrize("side", ["right", "left"])
def test_canopy_roof_is_unbroken_over_rsw1(side):
    """No reset poke-hole — the roof over RSW1 is solid, on both halves and after the fuse.

    Removed deliberately rather than relocated: a bore up through the BOTTOM part would end in
    the gap under the PCB (at PCB_SEAT_Z, no PCB hole at RSW1), reaching the board and not the
    button. Reset is by opening the case or the nice!nano's double-tap over USB-C."""
    rx, ry = C.pcb_to_case(*C.SW_RESET_POS)
    surf_z = CAN._canopy_roof_z(ry, CAN.canopy_ridge_top_z(side))
    assert _solid_at(build_canopy(side=side), rx, ry, surf_z - 0.75), \
        f"{side} canopy roof pierced over RSW1"
    top_rx = C.OUTER_WIDTH - rx if side == "left" else rx
    assert _solid_at(build_top_part(side), top_rx, ry, surf_z - 0.75), \
        f"{side} TOP roof pierced over RSW1"


@pytest.mark.parametrize("side", ["right", "left"])
def test_canopy_usb_port_open(side):
    """The port is a STEPPED bore: an overmold POCKET in the outer part of the north wall,
    then a shell-sized NECK the rest of the way. Probe each section at its own depth — a
    single mid-wall probe now lands inside the pocket and tells you nothing about the neck."""
    c = build_canopy(side=side)
    ncx = _mcu_cx()
    y_pocket = CAN.CANOPY_NORTH_OUTER_Y - CAN.CANOPY_USB_OM_DEPTH / 2
    y_neck = CAN.CANOPY_NORTH_OUTER_Y - CAN.CANOPY_USB_OM_DEPTH - 0.5

    lo, hi = CAN.canopy_usb_z(side)
    assert not _solid_at(c, ncx, y_neck, (lo + hi) / 2), f"{side} USB neck blocked"
    assert not _solid_at(c, ncx, y_neck, hi - 0.3), f"{side} USB neck short at the top"
    assert _solid_at(c, ncx, y_neck, hi + 0.6), f"{side} USB neck overshoots above the band"
    assert _solid_at(c, ncx + CAN.CANOPY_USB_W / 2 + 1.5, y_neck, (lo + hi) / 2), \
        "north wall missing beside the neck"

    plo, phi = CAN.canopy_usb_om_z(side)
    assert not _solid_at(c, ncx, y_pocket, (plo + phi) / 2), f"{side} USB pocket blocked"
    assert not _solid_at(c, ncx, y_pocket, phi - 0.3), f"{side} USB pocket short at the top"
    assert _solid_at(c, ncx + CAN.CANOPY_USB_OM_W / 2 + 1.0, y_pocket, (plo + phi) / 2), \
        "north wall missing beside the pocket"
    # The pocket must be strictly wider than the neck, or the step does nothing.
    assert CAN.CANOPY_USB_OM_W > CAN.CANOPY_USB_W and (phi - plo) > (hi - lo)


@pytest.mark.parametrize("side", ["right", "left"])
def test_usb_port_cutter_corners_are_filleted(side):
    """The mouth is a ROUNDED rectangle. The fillet in ``usb_port_cutter`` is wrapped in a
    try/except that degrades to a square mouth rather than aborting the port, so assert the
    arcs are actually there — otherwise a silent OCC failure would go unnoticed."""
    cutter = CAN.usb_port_cutter(side)
    cyl = [f for f in cutter.faces() if f.geom_type == GeomType.CYLINDER]
    # EIGHT, not four: the stepped bore is two rounded-rectangle sections (pocket + neck).
    assert len(cyl) == 8, f"{side} mouth has {len(cyl)} rounded corners, expected 8"
    radii = {round(f.geom_adaptor().Cylinder().Radius(), 3) for f in cyl}
    assert radii == {round(CAN.CANOPY_USB_R, 3)}, f"unexpected corner radii: {radii}"
    # Rounding must not shrink either opening. The bounding box is the POCKET (the larger
    # section); the neck is checked through canopy_usb_z in test_canopy_usb_port_open.
    bb = cutter.bounding_box()
    plo, phi = CAN.canopy_usb_om_z(side)
    assert abs((bb.max.X - bb.min.X) - CAN.CANOPY_USB_OM_W) < 1e-6
    assert abs(bb.min.Z - plo) < 1e-6 and abs(bb.max.Z - phi) < 1e-6


@pytest.mark.parametrize("side", ["right", "left"])
def test_fused_top_usb_mouth_is_rounded_not_square(side):
    """On the FUSED TOP: material fills all four corners of the nominal rectangle, while the
    mid-span of every edge stays open — i.e. rounded, not pinched and not square."""
    top = build_top_part(side)
    cx = _mcu_cx()
    if side == "left":
        cx = C.OUTER_WIDTH - cx
    d = 0.25
    # Both sections of the stepped bore, each probed at its OWN depth and cross-section.
    sections = (
        ("neck", CAN.CANOPY_NORTH_OUTER_Y - CAN.CANOPY_USB_OM_DEPTH - 0.5,
         CAN.CANOPY_USB_W / 2, *CAN.canopy_usb_z(side)),
        ("pocket", CAN.CANOPY_NORTH_OUTER_Y - CAN.CANOPY_USB_OM_DEPTH / 2,
         CAN.CANOPY_USB_OM_W / 2, *CAN.canopy_usb_om_z(side)),
    )
    for label, yw, hw, lo, hi in sections:
        mid = (lo + hi) / 2
        for sx, sz, name in ((+1, +1, "NE"), (-1, +1, "NW"), (+1, -1, "SE"), (-1, -1, "SW")):
            z = (hi - d) if sz > 0 else (lo + d)
            assert _solid_at(top, cx + sx * (hw - d), yw, z, s=0.2), \
                f"{side} {label} {name} corner still square"
        for x, z, name in ((cx + hw - d, mid, "+X"), (cx - hw + d, mid, "-X"),
                           (cx, hi - d, "top"), (cx, lo + d, "bottom")):
            assert not _solid_at(top, x, yw, z, s=0.2), \
                f"{side} {label} pinched at the {name} edge"


def test_usb_port_delivers_the_engagement_target():
    """The whole point of the stepped bore: buy the plug shell enough ENGAGEMENT in the jack.

    The receptacle never swallows the whole shell — the wall hides the rest — so what matters
    is how much shell ends up inside. A straight shell-sized hole leaves only
    6.65 − 4.41 = 2.24 mm (34%) AND blocks the overmold on the outer face, i.e. that port
    would not take a standard cable at all. The pocket lets the overmold sink into the wall
    and the shell picks that depth up one-for-one.
    """
    engagement = C.USB_PLUG_SHELL_L + CAN.CANOPY_USB_OM_DEPTH - CAN.CANOPY_USB_TRAVEL
    assert abs(engagement - C.USB_PORT_ENGAGE_TARGET) < 1e-9, \
        f"stepped bore yields {engagement:.2f} mm, target {C.USB_PORT_ENGAGE_TARGET}"
    # The pocket must stop short of the jack — it is wall relief, not a bigger port.
    assert CAN.CANOPY_USB_OM_DEPTH < CAN.CANOPY_USB_TRAVEL, "pocket reaches the jack"
    # ...and must admit a worst-case USB-IF-compliant overmold, or "any cable fits" is a lie.
    assert CAN.CANOPY_USB_OM_W >= C.USB_OVERMOLD_W
    assert CAN.CANOPY_USB_OM_H >= C.USB_OVERMOLD_H


@pytest.mark.parametrize("side", ["right", "left"])
def test_usb_pocket_stays_buried_under_the_north_shoulder(side):
    """The pocket is 7 mm tall in a wall whose top edge is rounded away by
    CANOPY_NORTH_ROUND_R. If THIS half's ridge does not clear both, the pocket breaks out
    through the shoulder and the port stops being a closed hole — which no volume or bbox
    check catches.

    Checked PER HALF now that the ridge is per-half: the old form compared every half's pocket
    against the shared alias, which happened to be right's own ridge — so it silently verified
    right against itself while saying nothing about left."""
    pocket_top = CAN.canopy_usb_om_z(side)[1]
    ridge = CAN.canopy_ridge_top_z(side)
    assert ridge - CAN.CANOPY_NORTH_ROUND_R - pocket_top >= \
        CAN.CANOPY_USB_OM_ROOF_MIN - 1e-9, f"{side} pocket breaks into the north wall's round-over"


def test_ridge_to_port_offset_equal_across_halves():
    """The actual request behind the per-half ridge: both halves should carry the SAME amount
    of roof material above their own (differently-positioned) port, not a common ridge that
    buries the shorter-jack half under 2.76 mm of dead air. Both offsets — ridge-to-pocket-top
    and ridge-to-window-top — must match exactly between halves, since pocket and window are
    both derived the same way per side."""
    offsets_pocket = {s: CAN.canopy_ridge_top_z(s) - CAN.canopy_usb_om_z(s)[1] for s in ("left", "right")}
    offsets_window = {s: CAN.canopy_ridge_top_z(s) - CAN.canopy_usb_z(s)[1] for s in ("left", "right")}
    assert abs(offsets_pocket["left"] - offsets_pocket["right"]) < 1e-9, offsets_pocket
    assert abs(offsets_window["left"] - offsets_window["right"]) < 1e-9, offsets_window
    assert CAN.canopy_ridge_top_z("left") < CAN.canopy_ridge_top_z("right"), \
        "left carries the flipped (lower) jack band and should end up with the shorter ridge"


def test_canopy_usb_bands_differ_between_halves():
    """The halves carry opposite MCU orientations, so the port sits at a different Z on each.
    Probed in each half's exclusive band (they overlap only through 19.6–21.1)."""
    left, right = build_canopy(side="left"), build_canopy(side="right")
    ncx = _mcu_cx()
    yw = CAN.CANOPY_NORTH_OUTER_Y - CAN.CANOPY_SIDE_WALL / 2
    z_left_only, z_right_only = 17.5, 23.5
    assert not _solid_at(left, ncx, yw, z_left_only), "left port missing in its own band"
    assert _solid_at(right, ncx, yw, z_left_only), "right port reaches into the flipped band"
    assert not _solid_at(right, ncx, yw, z_right_only), "right port missing in its own band"
    assert _solid_at(left, ncx, yw, z_right_only), "left port reaches into the neutral band"


# ---------------------------------------------------------------------------
# Fused into the TOP
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("side", ["right", "left"])
def test_canopy_fused_into_top_single_solid(side):
    top = build_top_part(side)
    assert top.is_valid and len(top.solids()) == 1, f"{side} TOP not one valid solid"
    assert abs(top.bounding_box().max.Z - CAN.canopy_ridge_top_z(side)) < 0.01, \
        f"{side} TOP not raised to its own canopy ridge"


def test_usb_jack_stops_short_of_the_north_wall():
    """The mid-mount jack must NOT reach the canopy's north wall — only the plug bridges it.

    This is the guard for the MCU_BODY_L trap: the nano's USB-end face is anchored to its pin
    array, so a longer board grows southward. Centring it on MCU_POS instead drives the jack
    into the wall (0.14 mm at MCU_BODY_L = 34.1), which no geometry test would otherwise catch.
    """
    jack_end   = C.MCU_BODY_N_Y + C.USB_JACK_Y_PROTRUDE
    wall_inner = CAN.CANOPY_NORTH_OUTER_Y - CAN.CANOPY_SIDE_WALL
    assert jack_end < wall_inner, f"jack reaches the wall: {jack_end:.2f} >= {wall_inner:.2f}"
    assert wall_inner - jack_end > 0.3, "air gap under 0.3 mm — re-check the board Y anchor"


@pytest.mark.parametrize("side", ["right", "left"])
def test_fused_top_clears_all_bay_components(side):
    """The fused TOP (cover + canopy) must not touch any component above the cover.

    Probed against the SIDE-MATCHED phantom: the jack stub moves with the MCU orientation,
    so the right half must clear a jack at 20.40–23.56 and the left one at 17.64–20.80.

    The encoder is excluded deliberately. This test is about the components the canopy VAULTS
    OVER, and it is parameterized on the jack orientation for exactly that reason; the EC11 is the
    one component the cover is meant to touch — it passes THROUGH the membrane — so it answers a
    different question and gets its own test below."""
    top = build_top_part(side)
    if side == "left":
        top = _mirror_back(top)
    above = Solid.make_box(200, 200, 60).translate((-20, -20, C.COVER_TOP_Z + 0.1))
    # build123d raises on `empty & shape` rather than returning empty, and an empty first
    # intersection is the PASSING case here — so short-circuit instead of chaining blindly.
    touching = top & build_pcb_phantom(side, include_encoder=False)
    clash = (touching & above) if touching else None
    vol = 0.0 if clash is None else sum(s.volume for s in clash.solids())
    assert vol < 1e-2, f"{side} canopy clashes bay components by {vol:.2f} mm^3"


@pytest.mark.parametrize("side", ["right", "left"])
def test_cover_clears_the_encoder_body(side):
    """The cover must not occupy the space the EC11's own body stands in.

    This check could not exist before the encoder had a phantom: switch_phantom skips SW25 (it is
    not an MX switch) and pcb_phantom did not draw it, so the tallest object on the keyboard was
    being fit-checked against nothing at all. With it drawn, the plateau turned out to interfere by
    ~0.92 mm^3 in four equal lumps — one per body corner, Z 16.10–17.00 — a real collision with a
    brass-and-plastic part that will not yield. This carried an ``xfail(strict=True)`` while that
    stood.

    FIXED, and the print proved why it mattered: ``_encoder_shell`` selected its R3.0 plan
    round-over by edge LENGTH, so the cavity's four vertical corners (4.2 mm) were filleted along
    with the outer wall's, refilling them to r 8.32 against the body corners' 8.77. The fix filters
    that selection RADIALLY, leaving the cavity square — a square cavity is what clears a square
    body best, so the planned "round the cavity deliberately at a small radius" is not needed.

    This test only ever looked ABOVE ``COVER_TOP_Z``, so it saw 0.92 of the 2.03 mm^3;
    ``test_case.test_encoder_plateau_clears_the_ec11_body`` covers the body's full proud height
    and so also catches the membrane-window half of the pinch."""
    top = build_top_part(side)
    if side == "left":
        top = _mirror_back(top)
    above = Solid.make_box(200, 200, 60).translate((-20, -20, C.COVER_TOP_Z + 0.1))
    touching = top & build_encoder_phantom()
    clash = (touching & above) if touching else None
    vol = 0.0 if clash is None else sum(s.volume for s in clash.solids())
    assert vol < 1e-2, f"{side} cover clashes the encoder by {vol:.2f} mm^3"
