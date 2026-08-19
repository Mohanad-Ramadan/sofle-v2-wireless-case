"""The cover-side encoder styles, and the facts they are allowed to assume.

Every one of these pins something that HAS ALREADY GONE STALE ONCE. The style set was drawn
against an Ø18 knob that does not exist, a deck at Z 16.0 that has since moved to 16.4, and a
plate window quoted at Ø18.04 that measures Ø17.91. None of that was caught by a test, because
none of it was in one — the numbers only lived in comments and in constants derived from other
constants. These tests put the comparisons where a run can fail them.
"""
import math

import pytest
from build123d import Solid

from sofle_case import constants as C
from sofle_case import encoder_phantom as E
from sofle_case import knob as K
from sofle_case import case as CA


@pytest.fixture
def style(monkeypatch):
    """Set ENCODER_COVER_STYLE for one test without leaking it into the next."""
    def _set(name: str) -> str:
        monkeypatch.setattr(C, "ENCODER_COVER_STYLE", name)
        return name
    return _set


def test_cavity_estimate_tracks_the_real_plate_window():
    """``constants`` cannot call ``case._encoder_bbox`` (that would close an import cycle), so it
    carries the window size as literals. Literals drift; this is the only thing stopping them."""
    _, _, bbox_w, bbox_h = CA._encoder_bbox()
    assert C._ENC_WINDOW_W == pytest.approx(bbox_w, abs=1e-3)
    assert C._ENC_WINDOW_H == pytest.approx(bbox_h, abs=1e-3)


def test_the_ring_guard_and_the_constants_agree_on_the_cavity():
    """``_encoder_ring`` measures the cavity it actually cuts; ``constants`` estimates the same
    cavity at import time to guard the shipped dimensions. If the two disagree, one of the two
    checks is guarding a ring nobody builds."""
    _, _, bbox_w, bbox_h = CA._encoder_bbox()
    live = math.hypot((bbox_w + 2 * C.ENCODER_SHELL_CAVITY_CLEAR) / 2 - C.ENCODER_RING_CAVITY_R,
                      (bbox_h + 2 * C.ENCODER_SHELL_CAVITY_CLEAR) / 2 - C.ENCODER_RING_CAVITY_R)
    assert C._cav_corner_r == pytest.approx(live + C.ENCODER_RING_CAVITY_R, abs=1e-3)


def test_the_window_is_wider_than_the_knob():
    """The premise the whole style set was drawn on — "the window is the same size as the knob, so
    the cover can hide nothing inside the knob's outline" — is false, and the styles that assume a
    knob-covered aperture inherit that. Ø13 covers none of an Ø17.9 window."""
    _, _, bbox_w, bbox_h = CA._encoder_bbox()
    window_dia = math.hypot(bbox_w, bbox_h)
    assert window_dia > K.KNOB_OD + 4.0, (
        f"window Ø{window_dia:.2f} is no longer far wider than the Ø{K.KNOB_OD} knob — the "
        f"styles' aperture reasoning was written for that gap and needs rereading")
    assert C.ENCODER_APERTURE_DIA >= window_dia, "aperture must clear the window's corners"


def test_the_aperture_cannot_be_closed_down_to_the_knob():
    """Why every non-sealed style shows an annulus: the aperture's floor is the EC11 body's own
    diagonal, which is still far wider than the knob. Only a sealed roof hides the body."""
    body_dia = E.BODY_W * math.sqrt(2)
    assert body_dia > K.KNOB_OD, "the knob would now cover the body; the annulus argument changes"
    assert C.ENCODER_APERTURE_DIA > body_dia, "aperture must clear the encoder body's corners"


def test_ring_proud_tracks_the_z_stack_rather_than_a_literal():
    """MAIN_RIM_Z moved 15.0 -> 15.4 and took COVER_TOP_Z and ENCODER_BODY_TOP_Z with it. The ring
    survived only because its height is derived. Keep it derived."""
    assert C.ENCODER_RING_SEALED_MIN == pytest.approx(
        C.ENCODER_OBSTRUCTION_TOP_Z + C.ENCODER_RING_BOX_CLEAR + C.ENCODER_RING_ROOF - C.COVER_TOP_Z)
    assert C.ENCODER_RING_PROUD >= C.ENCODER_RING_SEALED_MIN


def test_plateau_height_is_the_knob_seating_datum():
    """``constants`` claims ENCODER_PLATEAU_H is the height at which a bezel top lands
    KNOB_HEM_CLEAR under the knob's bottomed hem, and both bezels are built to it on that basis.
    It cannot check the claim itself — ``knob`` imports ``constants``, not the other way round — so
    this is where it gets checked. If this fails, ENCODER_PLATEAU_H is what has to move."""
    seating_h = K.knob_hem_z_if_bottomed() - K.KNOB_HEM_CLEAR - C.COVER_TOP_Z
    assert C.ENCODER_PLATEAU_H == pytest.approx(seating_h), (
        f"ENCODER_PLATEAU_H {C.ENCODER_PLATEAU_H} no longer lands a bezel top "
        f"{K.KNOB_HEM_CLEAR} under the bottomed hem (wants {seating_h:.2f})")


def test_a_roof_over_the_encoder_clears_its_locating_leg_not_just_its_box():
    """The clash that the sealed ring found. ENCODER_BODY_TOP_Z is the BOX top; a metal leg stands
    0.8 mm above it, and a roof sized off the box buries it. The mound clears the leg only by luck
    of ENCODER_PLATEAU_H, so both roofs are checked here rather than trusting either."""
    assert C.ENCODER_OBSTRUCTION_TOP_Z == pytest.approx(E.BODY_TOP_Z + E.LEG_H), (
        "the phantom's leg and the clearance datum have drifted apart")
    ring_ceiling = C.COVER_TOP_Z + C.ENCODER_RING_PROUD - C.ENCODER_RING_ROOF
    assert ring_ceiling >= C.ENCODER_OBSTRUCTION_TOP_Z, (
        f"the ring's roof underside ({ring_ceiling:.2f}) sits inside the encoder's leg "
        f"({C.ENCODER_OBSTRUCTION_TOP_Z:.2f})")
    assert C.ENCODER_CAVITY_TOP_Z >= C.ENCODER_OBSTRUCTION_TOP_Z, (
        "the mound's roof underside now sits inside the encoder's leg")


def test_the_two_sealed_rings_differ_only_by_the_foot_groove():
    """"ring" (F6, shipped) and "ring_bevel" (F5) are the same collar with and without the shadow
    groove at its foot. They were different rings once — F was all-bevel at 1.5 — and converged
    when the K round gave both the same plain 0.8 chamfer.

    That convergence is load-bearing now, and it rests on a coincidence: the "ring" path builds its
    top face as BASE_DIA − 2 × CHAMFER, which lands back on TOP_DIA only while CHAMFER equals
    BEVEL_RUN. Reopening the bevel on one style would silently resize the shipped one. This fails
    first and says so."""
    assert C.ENCODER_RING_BASE_DIA == pytest.approx(19.5), "the K1 collar's foot has moved"
    assert C.ENCODER_RING_CHAMFER == pytest.approx(C.ENCODER_RING_BEVEL_RUN), (
        f"the plain chamfer ({C.ENCODER_RING_CHAMFER}) and the bevel run "
        f"({C.ENCODER_RING_BEVEL_RUN}) have come apart, so \"ring\" and \"ring_bevel\" are no "
        f"longer the same collar — decide what each diameter should be, not just one")
    ring_top = C.ENCODER_RING_BASE_DIA - 2 * C.ENCODER_RING_CHAMFER
    assert ring_top == pytest.approx(C.ENCODER_RING_TOP_DIA)


def test_f6_is_the_grooveless_ring():
    """F6 vs F5. The two rings are otherwise identical, so the only way the choice shows up in the
    geometry is that the grooveless one carries more material — the groove is a subtraction."""
    cx, cy, _, _ = CA._encoder_bbox()
    f6 = CA._encoder_ring(cx, cy, top_dia=C.ENCODER_RING_BASE_DIA - 2 * C.ENCODER_RING_CHAMFER,
                          bevel_run=C.ENCODER_RING_CHAMFER, bevel_drop=C.ENCODER_RING_CHAMFER,
                          groove=False, step=False)
    f5 = CA._encoder_ring(cx, cy)
    assert f6.volume > f5.volume, "the grooveless ring should carry MORE material than the grooved"


def test_whatever_ships_seats_the_knob_without_a_shaft_cut():
    """Deliberately does NOT name the shipped style. An earlier version of this test asserted
    ``== "ring"`` and had to be edited the moment the bezel changed again, which makes it churn
    rather than guard. What must never change is the PROPERTY: the shipped bezel reaches the
    seating datum, so nobody is asked to take a saw to the encoder shaft."""
    assert C.ENCODER_COVER_STYLE in SEATING_STYLES, (
        f"{C.ENCODER_COVER_STYLE!r} ships but stops short of the seating datum — it would need "
        f"the shaft cut, which knob.py records as a one-way near-miss")


# Styles built up to the seating datum, so the knob rests on them with no shaft cut. Every other
# style stops short of it and buys its look with bare Ø6 shaft on show under the knob.
SEATING_STYLES = ("mound", "ring", "ring_bevel", "two_step", "plinth")


def test_the_seating_styles_take_the_knob_without_cutting_the_shaft(style):
    """THE headline fact the brainstorm did not have. The knob bottoms on its own bore at a fixed
    Z; the cover only decides how much bare shaft shows under it, and trimming to close that gap is
    a one-way cut on metal. Numbers here are informational — the SPLIT is the invariant, so this
    fails loudly if a Z move ever silently reshuffles which styles land on the datum."""
    bottomed = K.knob_hem_z_if_bottomed()
    trims = {}
    for name in CA.ENCODER_COVER_STYLES:
        style(name)
        trims[name] = max(0.0, bottomed - (max(C.ENCODER_BODY_TOP_Z, E.BUSHING_TOP_Z,
                                               CA.encoder_feature_top_z()) + K.KNOB_HEM_CLEAR))
    seats = {k: v for k, v in trims.items() if k in SEATING_STYLES}
    shows = {k: v for k, v in trims.items() if k not in SEATING_STYLES}
    assert all(v == pytest.approx(0.0, abs=1e-6) for v in seats.values()), (
        f"a style built to the seating datum no longer seats untrimmed: {seats} — "
        f"ENCODER_PLATEAU_H and ENCODER_RING_PROUD must follow the Z stack")
    assert all(v > 0.0 for v in shows.values()), (
        f"a style that stops short of the datum now seats untrimmed: {shows} — if that is "
        f"intended, move it into SEATING_STYLES and say why")


def test_strokes_cuts_nothing_on_the_half_with_no_line_to_continue(style):
    """The style is "the canopy's own puzzle line, interrupted by the knob". On the left half the
    nearest line passes 26 mm away, so there is no interruption to draw — and a groove cut there
    would be a stray mark, not a continuation."""
    style("strokes")
    cx, cy, _, _ = CA._encoder_bbox()
    right = CA._stroke_grooves(cx, cy, "right")
    left = CA._stroke_grooves(cx, cy, "left")
    assert right, "the right half's line A passes under the knob and should still be cut"
    assert left == [], "the left half has no line near the encoder; it must cut nothing"


def test_the_right_hand_line_really_does_pass_under_the_knob(style):
    """If line A ever moves outside the knob's radius, "the knob interrupts the stroke" stops being
    true and the style needs redrawing rather than quietly cutting a tangent groove."""
    cx, cy, _, _ = CA._encoder_bbox()
    a, b, c = CA.PZ.line_in_canopy("right", 0)
    assert abs(a * cx + b * cy - c) < K.KNOB_OD / 2, "line A no longer runs under the knob"


def test_unknown_style_is_rejected_before_any_geometry_is_built(style):
    style("bare")          # one of four names the builder script used to advertise
    with pytest.raises(ValueError, match="unknown ENCODER_COVER_STYLE"):
        CA.apply_encoder_cover_style(None)


# --- "plinth": rounded square at the deck, small circle at the top ---------------------------

def test_the_plinth_cavity_is_square_and_clears_the_steel_box_corners():
    """Rounding a CONCAVE corner refills it, straight at the corners of the square steel EC11 body
    the cavity exists to clear. That is not theory: the mound's R3.0 plan round-over caught its
    cavity corners, bit 0.45 mm into each corner of the body, and held the printed TOP off the
    switch plate so the case rocked about the encoder.

    The sealed ring rounds its cavity at R1.5 deliberately — it needs the corners pulled in or its
    circular wall knife-edges — and pays for it with 0.133 mm to the body corners. The plinth's
    square skin has no such need, so it keeps the cavity square and gets 0.754 mm. FDM rounds
    internal corners on its own too, so the printed cavity is always tighter than the model."""
    assert C.ENCODER_PLINTH_CAVITY_R == 0.0, "the plinth cavity must stay square"
    _, _, bw, bh = CA._encoder_bbox()
    clr = C.ENCODER_SHELL_CAVITY_CLEAR
    cav_corner = math.hypot((bw + 2 * clr) / 2, (bh + 2 * clr) / 2)
    body_corner = math.hypot(E.BODY_W / 2, E.BODY_W / 2)
    assert cav_corner - body_corner > 0.5, (
        f"cavity corners reach r {cav_corner:.3f}, only {cav_corner - body_corner:.3f} mm clear "
        f"of the EC11 body corners at r {body_corner:.3f}")


def test_the_plinth_keeps_its_wall_at_the_cavity_corner_points():
    """With a SQUARE cavity inside a rounded skin the thinnest wall is the cavity's corner POINT
    against the skin's corner ARC — not the diagonal gap between the two outlines, which reads
    ~0.5 mm optimistic. While the skin's radius stays within the wall the binding point is on a
    flat instead, so the wall is simply the wall; past that the arc bites in, and at the R1.2 first
    chosen for this bezel it fell to 0.64."""
    r, w = C.ENCODER_PLINTH_CORNER_R, C.ENCODER_PLINTH_WALL
    wall = w if r <= w else r - (r - w) * math.sqrt(2)
    assert wall == pytest.approx(C._plinth_corner_wall)
    assert wall >= w, f"skin R{r} leaves {wall:.2f} mm at the cavity corner points"


def test_the_plinth_cavity_closes_above_the_encoders_leg():
    """The small circular top is bought by stepping the cavity in, and the step may not land on the
    encoder. It has to close at or above the LEG (ENCODER_OBSTRUCTION_TOP_Z), not the box top —
    that distinction is what the sealed ring got wrong and buried the leg by 0.7 mm."""
    assert C.ENCODER_PLINTH_STEP_Z >= C.ENCODER_OBSTRUCTION_TOP_Z, (
        f"cavity closes at {C.ENCODER_PLINTH_STEP_Z} — inside the leg at "
        f"{C.ENCODER_OBSTRUCTION_TOP_Z}")
    assert C.ENCODER_PLINTH_SHOULDER_Z - C.ENCODER_PLINTH_STEP_Z >= C.ENCODER_PLINTH_ROOF - 1e-9, (
        "the roof over the stepped cavity is thinner than ENCODER_PLINTH_ROOF")


def test_the_plinth_top_tucks_under_the_knob():
    """``constants`` sizes the circular top from the knob but cannot import ``knob`` to prove it.
    A 45° morph would land the top at Ø12.92 — 0.04 mm/side inside a Ø13 knob, which is not a tuck
    at any printable tolerance, so the tuck is stated and the angle is left to follow."""
    assert C.ENCODER_PLINTH_TOP_DIA == pytest.approx(
        K.KNOB_OD - 2 * C.ENCODER_PLINTH_TOP_TUCK)
    assert C.ENCODER_PLINTH_TOP_DIA < K.KNOB_OD


def test_the_plinth_only_ever_shrinks_going_up():
    """THE self-support claim, held as a test rather than a comment.

    The square→circle morph is 45° across the flats but ~74° at the corners, and that is only
    acceptable because no section is ever wider than the one below it — so printed bezel-up there
    is no overhang anywhere. If a future edit flares the form at any height this fails, and the
    printability argument in constants.py stops being true silently."""
    cx, cy, _, _ = CA._encoder_bbox()
    plinth = CA._encoder_plinth(cx, cy)
    prev_w = prev_h = float("inf")
    for z in (16.0, 17.0, 18.0, 19.0, 19.7, 20.0, 20.3, 20.6, 20.85):
        slab = Solid.make_box(60, 60, 0.05).translate((cx - 30, cy - 30, z))
        sect = plinth & slab
        if not sect or not sect.solids():
            continue
        bb = sect.bounding_box()
        w, h = bb.max.X - bb.min.X, bb.max.Y - bb.min.Y
        assert w <= prev_w + 1e-6 and h <= prev_h + 1e-6, (
            f"section at Z {z} ({w:.3f} x {h:.3f}) is wider than the one below "
            f"({prev_w:.3f} x {prev_h:.3f}) — the bezel flares and no longer self-supports")
        prev_w, prev_h = w, h


def test_the_plinth_is_smaller_than_the_ring_it_replaces():
    """The whole point. A circle has to span the SQUARE cavity's corners, so it wastes material
    across its flats; a square skin does not. If this ever stops holding, the plinth has no reason
    to exist over the simpler ring."""
    cx, cy, _, _ = CA._encoder_bbox()
    bb = CA._encoder_plinth(cx, cy).bounding_box()
    for extent, axis in ((bb.max.X - bb.min.X, "X"), (bb.max.Y - bb.min.Y, "Y")):
        assert extent < C.ENCODER_RING_BASE_DIA, (
            f"plinth is {extent:.2f} across {axis}, no tighter than the Ø"
            f"{C.ENCODER_RING_BASE_DIA} ring")


def test_the_cavity_corner_has_room_for_the_printed_fillet_without_a_dogbone():
    """Why there are no corner reliefs here, recorded so the question does not get reopened blind.

    FDM cannot print a sharp internal corner: the nozzle leaves a fillet, so the printed cavity
    corner always carries material the model does not. The usual answer is a dog-bone relief. This
    cavity does not need one — squaring it left 0.754 mm at the corners, and a 0.4 mm printed
    fillet intrudes only 0.166 mm along the diagonal.

    A dog-bone would also not be free. The skin's corner arc is centred on the cavity's corner
    point (skin R equals the wall), so the wall there is a uniform annulus and a relief eats it
    1:1 — r0.3 would take it to 0.5, under the minimum, unless the flats grow by the same amount
    and give back part of what the square skin won.

    If the cavity clearance ever drops toward the printed-fillet intrusion, this fails and the
    relief question genuinely reopens."""
    _, _, bw, bh = CA._encoder_bbox()
    clr = C.ENCODER_SHELL_CAVITY_CLEAR
    corner_clear = (math.hypot((bw + 2 * clr) / 2, (bh + 2 * clr) / 2)
                    - math.hypot(E.BODY_W / 2, E.BODY_W / 2))
    worst_fillet = 0.4 * (math.sqrt(2) - 1)          # a 0.4 mm printed radius, along the diagonal
    assert corner_clear > 3 * worst_fillet, (
        f"corner clearance {corner_clear:.3f} mm is no longer comfortably clear of the "
        f"{worst_fillet:.3f} mm a printed fillet intrudes — a dog-bone relief may now be needed")
    # And the wall really is the uniform annulus the argument above depends on.
    assert C.ENCODER_PLINTH_CORNER_R == pytest.approx(C.ENCODER_PLINTH_WALL), (
        "the skin's corner arc is no longer centred on the cavity's corner point, so the "
        "dog-bone cost argument in this test no longer holds")
