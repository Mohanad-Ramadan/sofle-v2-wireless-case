"""Metal knob phantom and seating arithmetic; never part of the printed case.

The fitted knob is a straight Ø13 × 17 mm push-fit part with a measured 16 mm-deep
Ø6 bore. On the 20 mm EC11 shaft, its hem lands 4 mm above the mounting face and
clears the encoder body by 0.5 mm. Keep the measured bore depth explicit: cutting
the shaft shorter than the bore would make the knob bottom on the encoder body.
"""
from __future__ import annotations

from typing import cast

from build123d import Part, Solid

from . import constants as C
from . import encoder_phantom as E

KNOB_OD = 13.0
KNOB_H = 17.0
KNOB_BORE_DIA = 6.0
KNOB_BORE_DEPTH = 16.0
KNOB_HEM_CLEAR = 0.5


def _seating_floor() -> tuple[str, float]:
    """Name and Z of the tallest encoder feature beneath the knob hem."""
    return max(
        (("encoder body", C.ENCODER_BODY_TOP_Z), ("bushing top", E.BUSHING_TOP_Z)),
        key=lambda feature: feature[1],
    )


def knob_hem_z() -> float:
    """Case Z of the knob's hem — the lowest it can sit, plus the design gap.

    The encoder body is currently the floor; the bushing remains in the calculation
    so a future measured collar cannot silently intersect the knob.
    """
    return _seating_floor()[1] + KNOB_HEM_CLEAR


def knob_hem_z_if_bottomed() -> float:
    """Case Z of the hem if the knob is simply pushed on until its bore bottoms on the shaft.

    This is the physical seating position for the untrimmed 20 mm shaft.
    """
    return E.SHAFT_TOP_Z - KNOB_BORE_DEPTH


def through_bore_hem_z() -> float:
    """Case Z of the hem if the bore went CLEAN THROUGH the knob — the lowest a knob of this height
    could ever reach on an untrimmed shaft, and the check on whether boring is even the lever."""
    return E.SHAFT_TOP_Z - KNOB_H


def bushing_is_the_stop() -> bool:
    """True when the bore is deep enough to swallow the whole shaft before the hem clears the
    collar — so the knob lands ON the Ø7 bushing and the design gap is unreachable by trimming.

    Trimming makes this WORSE, not better: it lowers the bottomed hem further into the collar. The
    fix there is a shallower bore, a taller bushing stack (nut/washer), or a knob with a recess."""
    return knob_hem_z_if_bottomed() < knob_hem_z()


def shaft_len_for_seating() -> float:
    """Shaft length, from the mounting face, that makes the SHAFT ITSELF the stop: the bore bottoms
    out exactly as the hem reaches ``knob_hem_z``.

    Capped at the as-bought length, because a shaft can be cut and never grown. When the cap binds,
    ``bushing_is_the_stop`` is True and no cut helps."""
    return min(E.SHAFT_LEN, knob_hem_z() + KNOB_BORE_DEPTH - E.BODY_TOP_Z)


def shaft_trim_needed() -> float:
    """How much shaft must come off for the knob to reach ``knob_hem_z`` (0 if it already does)."""
    return max(0.0, knob_hem_z_if_bottomed() - knob_hem_z())


def knob_seating_report() -> str:
    floor_name, floor_z = _seating_floor()
    head = (f"knob Ø{KNOB_OD}×{KNOB_H}, bore {KNOB_BORE_DIA}×{KNOB_BORE_DEPTH} | "
            f"design hem Z {knob_hem_z():.2f} (floor: {floor_name} {floor_z:.2f} + "
            f"{KNOB_HEM_CLEAR}) | bottomed-on-shaft hem Z {knob_hem_z_if_bottomed():.2f}")
    if bushing_is_the_stop():
        return (f"{head} | BORE TOO DEEP: the knob bottoms {knob_hem_z() - knob_hem_z_if_bottomed():.2f}"
                f" mm inside the Ø{E.BUSHING_DIA} bushing, so it lands on the collar. Cutting the "
                f"shaft cannot fix this")
    trim = shaft_trim_needed()
    on_show = knob_hem_z_if_bottomed() - floor_z
    tail = f"as-assembled bare shaft above the {floor_name} ({floor_z:.2f}): {on_show:.2f} mm"
    if trim > 0:
        tail += (f" — closing it to the {KNOB_HEM_CLEAR} design gap means cutting {trim:.2f} mm "
                 f"off the shaft ({E.SHAFT_LEN} → {shaft_len_for_seating():.2f}), which is "
                 f"one-way")
    return f"{head} | shaft trim needed {trim:.2f} mm | {tail}"


def build_knob_phantom(bottomed: bool = False) -> Part:
    """The knob in case coordinates. ``bottomed`` shows where it lands on an untrimmed shaft."""
    hem = knob_hem_z_if_bottomed() if bottomed else knob_hem_z()
    body = Solid.make_cylinder(KNOB_OD / 2, KNOB_H).translate((0, 0, hem))
    bore = Solid.make_cylinder(KNOB_BORE_DIA / 2, KNOB_BORE_DEPTH).translate((0, 0, hem))
    knob = cast(Part, body - bore)
    ex, ey = C.pcb_to_case(*C.SW_ENCODER_POS)
    return cast(Part, knob.translate((ex, ey, 0)))


def place_knob(bottomed: bool = False) -> Part:
    """The knob in RIGHT-HAND case coordinates — the caller mirrors it for the left half, exactly
    as the case itself is built right-handed and then mirrored."""
    return build_knob_phantom(bottomed=bottomed)


if __name__ == "__main__":
    from ocp_vscode import show

    from .encoder_phantom import build_ec11
    print(knob_seating_report())
    show(place_knob(), place_knob(bottomed=True), build_ec11(), build_ec11(trimmed=False),
         names=["knob(design seating)", "knob(untrimmed shaft)",
                f"ec11(shaft cut to {shaft_len_for_seating():.2f})",
                f"ec11(as bought, {E.SHAFT_LEN} shaft)"])
