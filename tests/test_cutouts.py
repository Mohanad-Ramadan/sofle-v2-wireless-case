def test_slide_scoop_is_a_solid():
    from sofle_case.case import _slide_scoop
    scoop = _slide_scoop()
    assert scoop.volume > 0, "slide-switch scoop cutter is empty"
    assert len(scoop.solids()) == 1, "slide-switch scoop cutter is not one solid"


# ----- Slide-switch actuator drop-in pocket ------------------------------------
from typing import cast

import pytest
from build123d import Part, Solid, Box, Location, BuildPart, Locations

from sofle_case import constants as C
from sofle_case.pcb_geometry import slide_switch_placement, rotate_2d


def _switch_body() -> Part:
    """SK12D07VG3 metal can solid, built from OWNED structural constants + SW31 placement."""
    cx, cy, rot = slide_switch_placement()
    body_z = C.PCB_TOP_Z + C.SLIDE_ACTUATOR_BODY_H / 2
    bdx, bdy = rotate_2d(C.SLIDE_ACTUATOR_PIN_CENTER_X, 0.0, rot)
    with BuildPart() as bp:
        with Locations(Location((cx + bdx, cy + bdy, body_z), (0, 0, rot))):
            Box(C.SLIDE_ACTUATOR_BODY_L, C.SLIDE_ACTUATOR_BODY_W, C.SLIDE_ACTUATOR_BODY_H)
    assert bp.part is not None
    return bp.part


def _switch_nub() -> Part:
    """Actuator nub solid, built from OWNED structural constants + SW31 placement."""
    cx, cy, rot = slide_switch_placement()
    nub_z = C.PCB_TOP_Z + 1.5 + C.SLIDE_ACTUATOR_NUB_H / 2
    ndx, ndy = rotate_2d(
        C.SLIDE_ACTUATOR_PIN_CENTER_X,
        -(C.SLIDE_ACTUATOR_BODY_W / 2 + C.SLIDE_ACTUATOR_NUB_D / 2),
        rot,
    )
    with BuildPart() as bp:
        with Locations(Location((cx + ndx, cy + ndy, nub_z), (0, 0, rot))):
            Box(C.SLIDE_ACTUATOR_NUB_L, C.SLIDE_ACTUATOR_NUB_D, C.SLIDE_ACTUATOR_NUB_H)
    assert bp.part is not None
    return bp.part


def _footprint_bbox():
    """Combined can+nub plan bbox (x0, x1, y0, y1) in case coords."""
    bb_b = _switch_body().bounding_box()
    bb_n = _switch_nub().bounding_box()
    return (
        min(bb_b.min.X, bb_n.min.X), max(bb_b.max.X, bb_n.max.X),
        min(bb_b.min.Y, bb_n.min.Y), max(bb_b.max.Y, bb_n.max.Y),
    )


def test_slide_actuator_cavity_is_a_solid():
    from sofle_case.case import _slide_actuator_cavity
    cav = _slide_actuator_cavity()
    assert cav.volume > 0, "actuator cavity cutter is empty"
    assert len(cav.solids()) == 1, "actuator cavity cutter is not one solid"
    bb = cav.bounding_box()
    # Poured from the seam to the cover underside — never perforates the lid.
    assert abs(bb.min.Z - C.SLIDE_ACTUATOR_FLOOR_Z) < 1e-6
    assert abs(bb.max.Z - C.SLIDE_ACTUATOR_TOP_Z) < 1e-6


@pytest.mark.parametrize("side", ["right", "left"])
def test_top_part_single_valid_solid_with_cavity(side):
    """The extra drop-in cut must leave the TOP part one valid manifold solid."""
    from sofle_case.case import build_top_part
    top = build_top_part(side)
    assert top.is_valid, f"TOP part invalid after actuator cavity cut ({side})"
    assert len(top.solids()) == 1, f"TOP part is not a single solid ({side})"


def test_slide_switch_clears_top_solid():
    """The physical switch (can + nub) has ZERO overlap with the TOP solid — the
    drop-in pocket gives ≥0.5 mm clearance all round (the nub previously collided)."""
    from sofle_case.case import build_top_part
    top = build_top_part("right")
    body_hit = cast(Part, _switch_body() & top).volume
    nub_hit = cast(Part, _switch_nub() & top).volume
    assert body_hit < 1e-6, f"switch can collides TOP by {body_hit:.4f} mm^3"
    assert nub_hit < 1e-6, f"actuator nub collides TOP by {nub_hit:.4f} mm^3"


def test_slide_actuator_pad_gap_is_real():
    """A grown probe (footprint + 0.4 mm, INSIDE the 0.5 mm pad) still has zero
    overlap with the TOP solid — proving the clearance gap is genuine, not coincident.
    Checked over the pocket's OWN Z extent (floor → SLIDE_ACTUATOR_TOP_Z cap); the can's
    clearance up to its full 12.2 top is covered separately by test_slide_switch_clears_top_solid."""
    from sofle_case.case import build_top_part
    top = build_top_part("right")
    x0, x1, y0, y1 = _footprint_bbox()
    g = 0.4
    z0, z1 = C.PCB_TOP_Z, C.SLIDE_ACTUATOR_TOP_Z  # 7.9 .. cavity cap (the pocket's own Z span)
    probe = Solid.make_box(
        (x1 - x0) + 2 * g, (y1 - y0) + 2 * g, z1 - z0
    ).translate((x0 - g, y0 - g, z0))
    # build123d returns None for an empty intersection — which is exactly the passing case.
    overlap = probe & top
    hit = 0.0 if overlap is None else cast(Part, overlap).volume
    assert hit < 1e-6, f"grown 0.4 mm probe overlaps TOP by {hit:.4f} mm^3 — pad gap not real"


def test_slide_drop_in_channel_is_clear():
    """Switch clearance column: across the switch footprint grid, the TOP solid has NO
    material anywhere over the switch body's Z span (PCB top 7.9 → 12.2), so the tub
    lowers over the switch (or the switch drops in) without collision.

    NB the lower bound is the switch-body base (PCB_TOP_Z), not the cavity floor: the
    tub now owns the full outer skin to the ground, so the −X wall is legitimately
    solid BELOW the switch (Z < 7.9) where part of the footprint bbox overlaps the wall
    band — that material never touches the switch, which sits entirely above PCB top."""
    from sofle_case.case import build_top_part
    top = build_top_part("right")
    x0, x1, y0, y1 = _footprint_bbox()

    def solid_at(x, y, z, e=0.1):
        b = Solid.make_box(2 * e, 2 * e, 2 * e).translate((x - e, y - e, z - e))
        return cast(Part, top & b).volume > 1e-7

    xs = [x0 + (x1 - x0) * i / 6 for i in range(1, 6)]
    ys = [y0 + (y1 - y0) * i / 8 for i in range(1, 8)]
    zs = [C.PCB_TOP_Z + (12.2 - C.PCB_TOP_Z) * i / 8 for i in range(9)]
    for z in zs:
        hits = sum(1 for x in xs for y in ys if solid_at(x, y, z))
        assert hits == 0, f"channel blocked: {hits} solid hits at Z={z:.3f}"


def test_slide_cavity_does_not_perforate_lid():
    """The pocket is capped at the cover underside (SLIDE_ACTUATOR_TOP_Z=12.5) so it
    CANNOT perforate the 1.0 mm lid: the cutter has zero material at/above 12.5, and
    the TOP still carries solid (cover/wall) material above 12.5 over the footprint —
    that band is provably untouched by a cut that lives entirely below it.

    (The slide switch sits in the open MCU/OLED/slide bay notch and behind the
    top-open finger scoop, so there is no continuous membrane directly over it; the
    invariant that matters is that THIS feature removes nothing above the cap.)"""
    from sofle_case.case import build_top_part, _slide_actuator_cavity
    x0, x1, y0, y1 = _footprint_bbox()

    # Slab from the cover underside up through the lid, over the whole padded footprint.
    px0, px1 = x0 - C.SLIDE_ACTUATOR_PAD, x1 + C.SLIDE_ACTUATOR_PAD
    py0, py1 = y0 - C.SLIDE_ACTUATOR_PAD, y1 + C.SLIDE_ACTUATOR_PAD
    lid_slab = Solid.make_box(px1 - px0, py1 - py0, 3.0).translate(
        (px0, py0, C.SLIDE_ACTUATOR_TOP_Z))

    def vol(x):
        return 0.0 if x is None else x.volume

    cav = _slide_actuator_cavity()
    assert vol(cav & lid_slab) < 1e-9, "cavity cutter intrudes above the cover underside"

    top = build_top_part("right")
    assert vol(top & lid_slab) > 1.0, "no cover/wall material above the cap — lid missing"


@pytest.mark.parametrize("side", ["right", "left"])
def test_slide_cavity_leaves_bottom_unchanged(side):
    """The slide cavity is a TOP-only feature; the BOTTOM is a separate inset plate
    below the rabbet ledge, so its volume is independent of the slide cavity. Baseline
    is the inset floor plate + standoffs − battery pocket (identical both sides)."""
    from sofle_case.case import build_bottom_part
    # Baseline reflects FLOOR_THICKNESS=6.3 (deep-battery redesign): the inset plate spans
    # floor→SEAM_LEDGE_Z, which rose with the floor, so the plate is taller than before.
    # 1e-2 abs tolerates OCC mirror/heal float noise on the left half (~3e-3).
    assert abs(build_bottom_part(side).volume - 72618.786656) < 1e-2
