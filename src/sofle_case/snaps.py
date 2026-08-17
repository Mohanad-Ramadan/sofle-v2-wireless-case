"""Rabbet snap latches — hold-shut for the case ends the 5 screws cannot reach.

The screws span case Y 35.5-96.7 of a 126 mm case, so both ends are unclamped cantilevers held
only by SEAM_FIT_CLEAR of rabbet friction. These latches hold those ends. They are NOT a second
clamp: the screws remain the only precision Z reference, and a fatigued latch degrades this
joint back to friction-only rather than letting the case open.

**Every flexing part is on the BOTTOM plate's rim, and that is a print-orientation decision.**
An FDM arm has to bend PARALLEL to the layer lines. A strip of the bottom's rim, freed by a slot
and pushed inward, bends about a VERTICAL axis, so the stretched material runs along the
extrusions. An arm hanging off the tub's ledge would bend about a horizontal axis and peel its
layers apart — and the tub prints rim-down, so that is squarely across them. See the "Rabbet
snap latch" block in ``constants.py`` for the full comparison.

Per arm, three cuts and one addition::

    plan view, looking down on the bottom plate's rim
    ═══════════════════════════════════════════════════════════
     plate floor
                ⊙━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
                ↑     inboard leg: frees the arm, and runs   ┃ ← outboard leg:
           root relief   down through the wedge to the       ┃   cuts THROUGH the
           (drilled)     ground face as the release port     ┃   rim, making the
     rim  ═══════════════════════════════[barb]═════════════━╋══  strip a CANTILEVER
          ↑                                                  ↑
          attached here only        ← arm.length →         free end
    ═══════════════════════════════════════════════════════════
     outside — the tub's skirt covers this, or the reveal shows the cut

and one cut in the TOP: the catch pocket in the skirt's inner face, opposite the barb.

The outboard leg is not optional. Freeing the strip with the inboard leg alone leaves it built
in at both ends, and a fixed-fixed strip strains ``12*d*h/L^2`` against a cantilever's
``3*d*h/(2*L^2)`` — 2.84% at L=22, which fractures PLA.

Local frame per arm: +u along the arm (root -> free), +v OUTWARD, w = Z. The rotation is
derived from the OUTWARD NORMAL ALONE, so "local +Y is outward" holds for every arm by
construction. ``SnapArm.sense`` then flips the arm's direction WITHIN that frame — it is not
folded into the rotation, because rotating to face the other way would also flip +v and every
radial sign with it.
"""
from __future__ import annotations
import math
from typing import cast

from build123d import (
    BuildLine, BuildPart, BuildSketch, Location, Part, Plane, Polyline, Solid, extrude,
    make_face,
)

from . import constants as C

# Radial (local +v) landmarks of the rabbet cross-section, measured from the rim's OUTER face:
_RIM_INNER_V = -C.SEAM_RIM_THK              # -2.55; rim's inboard face
_SKIRT_INNER_V = C.SEAM_FIT_CLEAR           # +0.20; tub skirt's inboard face


def _local_box(u0: float, u1: float, v0: float, v1: float, z0: float, z1: float) -> Part:
    u0, u1 = min(u0, u1), max(u0, u1)
    return cast(Part, Solid.make_box(u1 - u0, v1 - v0, z1 - z0).translate((u0, v0, z0)))


def arm_direction(out_x: float, out_y: float, sense: float = 1.0) -> tuple[float, float]:
    """Unit vector along the arm in CASE coords, root -> free end."""
    return (sense * out_y, sense * -out_x)


def arm_angle(out_x: float, out_y: float) -> float:
    """Rotation that maps local +Y onto the outward normal. Independent of ``sense``."""
    return math.degrees(math.atan2(-out_x, out_y))


def _placed(part: Part, arm: C.SnapArm) -> Part:
    return cast(Part, Location((arm.root[0], arm.root[1], 0.0),
                               (0.0, 0.0, arm_angle(*arm.out))) * part)


def _slot_v0(arm: C.SnapArm) -> float:
    """Inboard edge of the relief slot. The slot is measured from the arm's INNER face, so a
    thinner arm means a WIDER slot — the arm is thinned by eating the rim from the inboard
    side, which is the only side that opens on nothing anybody sees."""
    return -(arm.thickness + C.SNAP_TAB_SLOT_W)


def barb_u(arm: C.SnapArm) -> float:
    """Where along the arm the barb sits: near the FREE end, where the arm actually deflects
    (the cantilever strain formula assumes tip loading).

    CLAMPED so the barb stays ON the arm. 0.8L is the target, but the barb is
    SNAP_BARB_X_LEN long, so on a short arm 0.8L puts its outboard half past the free end and
    into the relief slot — where it is fused back in AFTER the slot is cut and quietly plugs
    it, welding the arm to the rim it is supposed to be free of. At L=22 the clamp is inactive
    to 4 decimal places (17.6 either way); it bites only on the short N2."""
    return arm.sense * min(0.8 * arm.length,
                           arm.length - C.SNAP_BARB_X_LEN / 2.0 - 0.4)


def cut_u(arm: C.SnapArm) -> float:
    """Local u of the outboard leg's centre — the thing that has to be hidden."""
    return arm.sense * (arm.length + C.SNAP_TAB_SLOT_W / 2.0)


def _slot_z() -> tuple[float, float]:
    """Z span of the relief slot: the plate's full height, continued down past the wedge's
    ground face so the release port opens on the underside at every arm. The wedge deepens
    northward, so the floor is taken from the deepest point and the surplus just cuts air."""
    from .case import wedge_deep_z
    return wedge_deep_z() - 1.0, C.SEAM_LEDGE_Z


def _barb_local(arm: C.SnapArm, proud: float = C.SNAP_BARB_PROUD) -> Part:
    """Barb as ONE prism swept along the wall, standing on the rim's outer face (v = 0).

    Its section is the three points the two ramp angles define — ``(0, z_lo)``, the crest at
    ``(proud, z_mid)``, and ``(0, z_hi)`` — so the crest lands on ``proud`` EXACTLY, by
    construction rather than by sampling.

    This used to be a Z-stack of 0.04 mm slabs, each sampled at the edge nearer the crest
    because midpoint sampling landed the crest 0.019 mm shallow — a 3% error on the latch's
    governing dimension. SNAP_RETURN_DEG = 90 retires the whole problem: with a flat return
    face the section is a plain right triangle, and even at a shallower return it is still just
    a triangle with the crest partway up. The staircase also cost ~470 faces across nine barbs,
    which is what made test_the_band_is_one_smooth_wall fire.

    Bottom face at ``arm.barb_lo_z``. At 90° it is FLAT and the barb starts at full depth — a
    pure undercut that cannot cam out, and also the SHORTEST barb in Z, because a return ramp
    costs proud/tan(angle) of height and a flat one costs nothing. Above the crest the lead-in
    face falls back to v=0 at SNAP_LEAD_IN_DEG, so the descending skirt cams the arm aside.
    """
    lead_run = proud / math.tan(math.radians(C.SNAP_LEAD_IN_DEG))
    ret_run = (0.0 if C.SNAP_RETURN_DEG >= 90.0
               else proud / math.tan(math.radians(C.SNAP_RETURN_DEG)))
    z_lo = arm.barb_lo_z
    z_mid = z_lo + ret_run
    z_hi = z_mid + lead_run
    u0 = barb_u(arm) - C.SNAP_BARB_X_LEN / 2

    # Section in the local (v, z) plane. Plane.YZ maps sketch-x -> local +v and sketch-y -> Z,
    # and its normal is local +u, so offsetting it puts the section at the barb's near end.
    with BuildPart() as bp:
        with BuildSketch(Plane.YZ.offset(u0)):
            with BuildLine():
                Polyline((0.0, z_lo), (proud, z_mid), (0.0, z_hi), close=True)
            make_face()
        # dir= is mandatory: a face whose own normal points -u would otherwise extrude the
        # wrong way and hand back a barb on the inside of the rim. See AGENTS.md.
        extrude(amount=C.SNAP_BARB_X_LEN, dir=(1.0, 0.0, 0.0))
    assert bp.part is not None
    return cast(Part, bp.part)


def _relief_local(arm: C.SnapArm) -> Part:
    """The L-shaped slot that frees one arm, plus its drilled root relief."""
    z0, z1 = _slot_z()
    v0 = _slot_v0(arm)
    inboard = _local_box(0.0, arm.sense * arm.length, v0, -arm.thickness, z0, z1)
    # outboard leg: through the full rim at the free end -> cantilever, not fixed-fixed
    outboard = _local_box(arm.sense * arm.length,
                          arm.sense * (arm.length + C.SNAP_TAB_SLOT_W), v0, 0.0, z0, z1)
    # drilled root relief: a real radius at the root, with none of a fillet op's failure modes
    root = cast(Part, Solid.make_cylinder(C.SNAP_ROOT_FILLET, z1 - z0).translate(
        (0.0, (v0 - arm.thickness) / 2.0, z0)))
    return cast(Part, inboard + outboard + root)


def _catch_local(arm: C.SnapArm, proud: float = C.SNAP_BARB_PROUD) -> Part:
    """Catch pocket, cut into the tub skirt's inboard face opposite the barb.

    Floor at ``arm.barb_lo_z - SNAP_Z_PLAY`` — the retention face — with the barb's underside
    sitting SNAP_Z_PLAY above it, so the closure chain's one-directional error is absorbed
    BELOW the barb. That play is also the case's dead travel: the tub lifts by exactly it
    before the barb bites. Wider than the barb in u so the barb is never pinched at its ends,
    and 0.15 mm deeper than ``proud`` so it never bottoms out radially.
    """
    pad = 1.0
    return _local_box(
        barb_u(arm) - (C.SNAP_BARB_X_LEN / 2 + pad), barb_u(arm) + (C.SNAP_BARB_X_LEN / 2 + pad),
        _SKIRT_INNER_V - 0.1, _SKIRT_INNER_V + proud + 0.15,
        arm.barb_lo_z - C.SNAP_Z_PLAY, arm.barb_lo_z + C.snap_barb_h(proud))


def _at(arm: C.SnapArm, u: float) -> tuple[float, float]:
    """Case-coord point on the rim's outer face at local ``u``.

    Local +u is ``(out_y, -out_x)`` — the SENSE-FREE direction, matching ``arm_angle``'s
    rotation of local +X. The sense already lives in the sign of every ``u`` this is handed
    (``barb_u``, ``cut_u``), so applying it here too would cancel it out."""
    return (arm.root[0] + arm.out[1] * u, arm.root[1] - arm.out[0] * u)


def arm_free_end(arm: C.SnapArm) -> tuple[float, float]:
    return _at(arm, arm.sense * arm.length)


def barb_center(arm: C.SnapArm) -> tuple[float, float]:
    return _at(arm, barb_u(arm))


def cut_center(arm: C.SnapArm) -> tuple[float, float]:
    return _at(arm, cut_u(arm))


# ---------------------------------------------------------------------------
# N2 — the one arm that wraps the SW3 lobe's jog
# ---------------------------------------------------------------------------
# It cannot be built from local boxes like the others: it spans two north-facing runs and the
# 4.24 mm arc between them, and a straight prism laid across that arc floats off the wall and
# leaves disjoint solids — the failure that sank the first attempt at snaps entirely.
#
# So the slot is cut as a CONCENTRIC BAND instead. offset_extruded() already builds prisms
# offset from the PCB polygon, and the difference of two of them is an annulus that follows the
# outline exactly, arc included. Bounding that annulus to an X window and to y > the lobe's
# latitude selects precisely this stretch of it. Both bounds land on straight runs, so an
# axis-aligned bound is a perpendicular cut where it matters.


def _corner_s_to_xy(s: float) -> tuple[float, float]:
    """Point on the rim at arc-length ``s`` west from the lobe's east end.

    Only valid ON the two straight runs — the arc between them is skipped over, which is all
    the callers need: every feature this arm places (cut, root, barb) sits on a straight run,
    and the slot between them is built as a band rather than by walking ``s``."""
    (x0, y0), (x1, _y1) = C.SNAP_CORNER_LOBE
    lobe_len = x0 - x1
    if s <= lobe_len:
        return (x0 - s, y0)
    (wx0, wy0), _ = C.SNAP_CORNER_WEST
    return (wx0 - (s - lobe_len - C.SNAP_CORNER_ARC), wy0)


def corner_cut_center() -> tuple[float, float]:
    return _corner_s_to_xy(C.SNAP_CORNER_CUT_S + C.SNAP_TAB_SLOT_W / 2.0)


def corner_barb_center() -> tuple[float, float]:
    """0.8L from the root, i.e. near the free end — same rule as the straight arms."""
    free_s = C.SNAP_CORNER_CUT_S + C.SNAP_TAB_SLOT_W
    return _corner_s_to_xy(free_s + 0.2 * C.SNAP_CORNER_L)


def _corner_band(v_out: float, v_in: float, z0: float, z1: float) -> Part:
    """Annulus between two polygon offsets, trimmed to this arm's stretch of the outline."""
    from .tray import offset_extruded
    band = cast(Part, offset_extruded(v_out, z0, z1) - offset_extruded(v_in, z0, z1))
    free_s = C.SNAP_CORNER_CUT_S + C.SNAP_TAB_SLOT_W
    x_free = _corner_s_to_xy(free_s)[0]
    x_root = _corner_s_to_xy(free_s + C.SNAP_CORNER_L)[0]
    # y floor isolates the north stretch: the same annulus runs along the south edge at these X.
    win = _local_box(x_root, x_free, 100.0, 140.0, z0, z1)
    return cast(Part, band & win)


def corner_relief() -> Part:
    """Cutter for N2: inboard band + through-cut at the free end + drilled root relief."""
    z0, z1 = _slot_z()
    rim_out = C.PCB_XY_CLEARANCE + C.SEAM_RIM_THK              # 3.05, rim's outer face
    v_arm_in = rim_out - C.SNAP_CORNER_THK                     # 1.05, arm's inboard face
    v_slot_in = v_arm_in - C.SNAP_TAB_SLOT_W                   # -0.15, slot's inboard edge
    out = _corner_band(v_arm_in, v_slot_in, z0, z1)

    # Through-cut at the free end. On the lobe, which is a plain north-facing run, so a box.
    cx, cy = corner_cut_center()
    cut = _local_box(cx - C.SNAP_TAB_SLOT_W / 2, cx + C.SNAP_TAB_SLOT_W / 2,
                     cy - C.SEAM_RIM_THK - C.SNAP_TAB_SLOT_W, cy + 1.0, z0, z1)
    out = cast(Part, out + cut)

    # Root relief, on the far run, centred in the slot band's own thickness.
    free_s = C.SNAP_CORNER_CUT_S + C.SNAP_TAB_SLOT_W
    rx, ry = _corner_s_to_xy(free_s + C.SNAP_CORNER_L)
    y_mid = ry - rim_out + (v_arm_in + v_slot_in) / 2.0
    root = cast(Part, Solid.make_cylinder(C.SNAP_ROOT_FILLET, z1 - z0).translate(
        (rx, y_mid, z0)))
    return cast(Part, out + root)


def _corner_arm_record() -> C.SnapArm:
    """The corner arm dressed as a SnapArm so the barb and catch builders can place it.

    Legitimate because the barb and its pocket both sit on the LOBE, a plain north-facing run —
    only the relief has to follow the arc. ``root`` is the lobe's east end and the barb is
    reached by a negative u from there."""
    (x0, y0), _ = C.SNAP_CORNER_LOBE
    bx, _by = corner_barb_center()
    return C.SnapArm("N2-sw3-lobe", (x0, y0), (0.0, 1.0), -1.0,
                     x0 - bx + C.SNAP_BARB_X_LEN / 2 + 0.4,   # gives barb_u() = -(x0 - bx)
                     C.SNAP_CORNER_THK, C.SNAP_CORNER_BARB_LO_Z, False)


def corner_barb(proud: float = C.SNAP_BARB_PROUD) -> Part:
    arm = _corner_arm_record()
    return _placed(_barb_local(arm, proud), arm)


def corner_catch(proud: float = C.SNAP_BARB_PROUD) -> Part:
    arm = _corner_arm_record()
    return _placed(_catch_local(arm, proud), arm)


def _each(builder, *args) -> Part:
    out: Part | None = None
    for arm in C.SNAP_ARMS:
        placed = _placed(builder(arm, *args), arm)
        out = placed if out is None else cast(Part, out + placed)
    assert out is not None, "SNAP_ARMS is empty"
    return out


def snap_reliefs() -> Part:
    """Cutter: every arm's L-slot + root relief, N2's wrapped band included. Cut from BOTTOM."""
    return cast(Part, _each(_relief_local) + corner_relief())


def snap_barbs(proud: float = C.SNAP_BARB_PROUD) -> Part:
    """Adder: every arm's barb. Fuse onto the BOTTOM part AFTER the reliefs are cut."""
    return cast(Part, _each(_barb_local, proud) + corner_barb(proud))


def snap_catches(proud: float = C.SNAP_BARB_PROUD) -> Part:
    """Cutter: every catch pocket. Subtract from the TOP part."""
    return cast(Part, _each(_catch_local, proud) + corner_catch(proud))


def corner_wall_height() -> float:
    from .case import tent_ground_z
    return C.SEAM_LEDGE_Z - tent_ground_z(
        (C.SNAP_CORNER_LOBE[0][1] + C.SNAP_CORNER_WEST[0][1]) / 2.0)


def corner_strain() -> float:
    return C.snap_strain(C.SNAP_CORNER_THK, C.SNAP_CORNER_L)


def corner_force() -> float:
    return C.snap_force(C.SNAP_CORNER_THK, corner_wall_height(), C.SNAP_CORNER_L)


def arm_wall_height(arm: C.SnapArm) -> float:
    """Beam width ``b``: the local wall height the arm is freed out of, ground face to ledge.

    Not SEAM_LEDGE_Z — the wedge is 1.0 mm thick at the front and 14.24 at the back, so this
    runs 9.4 mm at the south front to ~20 mm at the north. Force goes as b, which is why arm
    thickness is set per arm."""
    from .case import tent_ground_z
    y0, y1 = arm.root[1], arm_free_end(arm)[1]
    return C.SEAM_LEDGE_Z - tent_ground_z((y0 + y1) / 2.0)


def snap_report() -> str:
    total = (sum(C.snap_force(a.thickness, arm_wall_height(a), a.length) for a in C.SNAP_ARMS)
             + corner_force())
    hidden = sum(1 for a in C.SNAP_ARMS if a.hidden_cut)
    lines = [
        f"snap latches: {len(C.SNAP_ARMS) + 1} arms, barb {C.SNAP_BARB_PROUD:.2f} mm proud "
        f"({C.SNAP_DEFLECT:.2f} deflection), lead-in {C.SNAP_LEAD_IN_DEG:.0f} deg / return "
        f"{C.SNAP_RETURN_DEG:.0f} deg",
        f"  barb {C.SNAP_BARB_H:.3f} mm tall, Z budget {C.SNAP_Z_BUDGET:.3f}, "
        f"{C.SNAP_Z_PLAY:.2f} mm of lift before it bites",
        f"  {hidden} cuts hidden, {len(C.SNAP_ARMS) + 1 - hidden} show a slit in the reveal",
        f"  total deflection force {total:.1f} N -> insertion "
        + " / ".join(f"{C.snap_insertion_force(total, mu):.1f}" for mu in (0.4, 0.5, 0.7))
        + " N at mu 0.4/0.5/0.7",
    ]
    for arm in C.SNAP_ARMS:
        fx, fy = arm_free_end(arm)
        bx, by = barb_center(arm)
        cx, cy = cut_center(arm)
        b = arm_wall_height(arm)
        lines.append(
            f"  {arm.name:<15} root ({arm.root[0]:6.2f},{arm.root[1]:6.2f}) -> free "
            f"({fx:6.2f},{fy:6.2f}), barb ({bx:6.2f},{by:6.2f}) Z {arm.barb_lo_z:.2f}, cut "
            f"({cx:6.2f},{cy:6.2f}) {'hidden' if arm.hidden_cut else 'SLIT'}, "
            f"L{arm.length:.0f} h{arm.thickness:.2f} b{b:5.2f} "
            f"eps {C.snap_strain(arm.thickness, arm.length) * 100:.3f}% "
            f"{C.snap_force(arm.thickness, b, arm.length):.2f} N")
    bx, by = corner_barb_center()
    cx, cy = corner_cut_center()
    lines.append(
        f"  {'N2-sw3-lobe':<15} root ({_corner_s_to_xy(C.SNAP_CORNER_CUT_S + C.SNAP_TAB_SLOT_W + C.SNAP_CORNER_L)[0]:6.2f},"
        f"{_corner_s_to_xy(C.SNAP_CORNER_CUT_S + C.SNAP_TAB_SLOT_W + C.SNAP_CORNER_L)[1]:6.2f}) "
        f"WRAPS the lobe jog, barb ({bx:6.2f},{by:6.2f}) Z {C.SNAP_CORNER_BARB_LO_Z:.2f}, cut "
        f"({cx:6.2f},{cy:6.2f}) SLIT, L{C.SNAP_CORNER_L:.0f} h{C.SNAP_CORNER_THK:.2f} "
        f"b{corner_wall_height():5.2f} eps {corner_strain() * 100:.3f}% {corner_force():.2f} N")
    return "\n".join(lines)


# %%
if __name__ == "__main__":
    print(snap_report())
