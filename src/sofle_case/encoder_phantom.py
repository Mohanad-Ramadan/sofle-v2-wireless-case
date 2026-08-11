"""PHANTOM of the EC11 encoder hardware — body, bushing, shaft, pins.

Never printed and never fused: it exists so renders show what the bezel actually surrounds, and so
the build can check the cover against the real part instead of against a bbox.

Part in use: EC11 rotary encoder, 5-pin, "20 mm" shaft, push switch
(https://www.ram-e-shop.com/shop/pot-ec11-rotary-5pin-20mm-ec11-rotary-encoder-with-push-button-switch-5pin-20mm-silver-9624).
That listing publishes only shaft Ø6 / ~20 mm, 20 detents, 5 pins, so everything else here comes
from the ALPS EC11E envelope the clones copy. MEASURED values are marked; the rest are the standard
envelope and are worth a caliper before anything depends on them.

The one number that is NOT cosmetic is ``SHAFT_LEN``. "20 mm" on these listings is normally
measured from the MOUNTING FACE (the top of the encoder body), and it decides how high the knob
ends up sitting — see ``knob.knob_hem_z`` and the report it prints.

That 20 mm is longer than the knob can take, so the build assumes the shaft is CUT: ``build_ec11``
draws it at ``knob.shaft_len_for_seating`` by default and ``trimmed=False`` gives the as-bought
part. Drawing the as-bought length by default made every render show a stub of shaft standing proud
of the knob's own top face — a picture of an assembly that cannot exist. ``knob`` owns that
arithmetic (it is the knob's bore and height that force the cut), which is why the import below is
function-local: ``knob`` reads THIS module for the untrimmed length.
"""
from __future__ import annotations
from typing import cast

from build123d import Part, Solid

from . import constants as C

# --- measured, already in constants.py -------------------------------------
BODY_TOP_Z = C.ENCODER_BODY_TOP_Z          # 17.0 — measured on the real board
BODY_H = BODY_TOP_Z - C.PCB_TOP_Z          # 6.6  — follows from the measurement

# --- standard EC11E envelope (assumed; verify with calipers) ---------------
BODY_W = 12.4          # mm; square body
BODY_LUG_W = 13.9      # mm; across the two mounting lugs (wider than the body in X)
BODY_LUG_H = 1.2       # mm; lug thickness, sitting at the body's base
BUSHING_DIA = 7.0      # mm; threaded collar, M7 × 0.75
BUSHING_H = 5.0        # mm; above the body top
SHAFT_DIA = 6.0        # mm; knurled
SHAFT_LEN = 20.0       # mm; from the mounting face (= body top), per the listing's "20 mm"
PIN_LEN = 3.5          # mm; below the PCB
PIN_W = 0.8

SHAFT_TOP_Z = BODY_TOP_Z + SHAFT_LEN       # 37.0 with the assumed 20 mm
BUSHING_TOP_Z = BODY_TOP_Z + BUSHING_H     # 22.0


def shaft_len_trimmed() -> float:
    """The cut length: how much shaft is left above the mounting face once it is trimmed to seat
    the knob. Lives in ``knob`` because the knob's height and bore are what set it."""
    from .knob import shaft_len_for_seating
    return shaft_len_for_seating()


def build_ec11(trimmed: bool = True) -> Part:
    """The encoder as it sits on the PCB, in RIGHT-HAND case coordinates.

    ``trimmed`` draws the shaft cut to length for the knob, which is how the assembly actually
    exists; ``trimmed=False`` is the as-bought part, for showing what has to come off.

    No ``side``: the case itself is built right-handed and mirrored as a whole, so phantoms follow
    the same rule and the caller mirrors them. Mirroring here as well would put the encoder back on
    the wrong half of a left build."""
    ex, ey = C.pcb_to_case(*C.SW_ENCODER_POS)
    shaft_len = shaft_len_trimmed() if trimmed else SHAFT_LEN

    body = Solid.make_box(BODY_W, BODY_W, BODY_H).translate(
        (ex - BODY_W / 2, ey - BODY_W / 2, C.PCB_TOP_Z))
    lugs = Solid.make_box(BODY_LUG_W, BODY_W * 0.5, BODY_LUG_H).translate(
        (ex - BODY_LUG_W / 2, ey - BODY_W * 0.25, C.PCB_TOP_Z))
    bushing = Solid.make_cylinder(BUSHING_DIA / 2, BUSHING_H).translate((ex, ey, BODY_TOP_Z))
    shaft = Solid.make_cylinder(SHAFT_DIA / 2, shaft_len).translate((ex, ey, BODY_TOP_Z))
    part = cast(Part, body + lugs + bushing + shaft)

    for dx in (-2.5, 0.0, 2.5):
        part = cast(Part, part + Solid.make_box(PIN_W, PIN_W, PIN_LEN).translate(
            (ex + dx, ey - BODY_W / 2, C.PCB_TOP_Z - PIN_LEN)))
    part.label = "ec11" if trimmed else "ec11(as bought)"
    return part


def build_encoder_phantom(with_knob: bool = True, trimmed: bool = True) -> Part:
    """The whole encoder ASSEMBLY: EC11 plus the knob pressed onto its shaft.

    The knob comes along by default because that is how the part exists on the desk — an EC11
    without its knob is never what you are checking the cover against. ``with_knob=False`` gives
    the bare hardware (for a scene that draws the knob itself, e.g. one showing both seatings).

    Imported inside the function: ``knob`` reads this module for the shaft length, so a top-level
    import back into it would be circular."""
    from .knob import place_knob
    children = [build_ec11(trimmed=trimmed)]
    if with_knob:
        knob = place_knob()
        knob.label = "knob"
        children.append(knob)
    assembly = Part(children=children)
    assembly.label = "encoder+knob" if with_knob else "encoder"
    return assembly


if __name__ == "__main__":
    from ocp_vscode import show
    from .knob import knob_seating_report
    print(knob_seating_report())
    show(build_encoder_phantom(), names=["encoder+knob"])
