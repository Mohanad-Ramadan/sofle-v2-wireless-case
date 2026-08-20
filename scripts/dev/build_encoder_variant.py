"""Build ONE cover-side encoder variant and export STLs for the render script.

Only the right half's TOP part is built (the bottom never sees the encoder), plus a PHANTOM of the
user's bought Ø13 × 17 metal knob so renders show the cover with the knob on. The phantom is never a
printed part.

Usage:
    python scripts/dev/build_encoder_variant.py <tag> [--no-knob]
        --style mound|ring|ring_bevel|two_step|plinth|reveal|engraved|strokes|racetrack

The style names are ``case.ENCODER_COVER_STYLES`` and nothing else — this line used to advertise
bare|circle|well|pad, four names the builder never grew, and passing one now fails fast.

Writes output/variants/<tag>_top.stl and <tag>_knob.stl.
"""
from __future__ import annotations
import sys
from pathlib import Path

from build123d import export_stl

from sofle_case import constants as C

OUT = Path("output/variants")


def main(argv: list[str]) -> None:
    tag = argv[0]
    args = argv[1:]
    style = C.ENCODER_COVER_STYLE
    want_knob = True
    for k, a in enumerate(args):
        if a == "--style":
            style = args[k + 1]
        elif a == "--no-knob":
            want_knob = False
        elif a == "--top-dia":
            C.ENCODER_RING_TOP_DIA = float(args[k + 1])
        elif a == "--bevel-run":
            C.ENCODER_RING_BEVEL_RUN = float(args[k + 1])
        elif a == "--bevel-drop":
            C.ENCODER_RING_BEVEL_DROP = float(args[k + 1])
        elif a == "--groove":            # "H,D", e.g. 1.0,0.6
            gh, gd = args[k + 1].split(",")
            C.ENCODER_RING_FOOT_GROOVE_H, C.ENCODER_RING_FOOT_GROOVE_D = float(gh), float(gd)
        elif a == "--no-groove":
            C.ENCODER_RING_FOOT_GROOVE_H = C.ENCODER_RING_FOOT_GROOVE_D = 0.0
    from sofle_case.case import ENCODER_COVER_STYLES
    if style not in ENCODER_COVER_STYLES:
        raise SystemExit(f"unknown --style {style!r}; expected one of {', '.join(ENCODER_COVER_STYLES)}")
    C.ENCODER_COVER_STYLE = style

    from sofle_case import knob as K
    from sofle_case.case import build_top_part, encoder_feature_top_z

    OUT.mkdir(parents=True, exist_ok=True)
    import math as _m

    # Report the style ACTUALLY being built. This printed the ring's diameter, bevel and groove for
    # every style, so a `--style plinth` run announced "top Ø17.9 base Ø19.50 bevel 0.8/0.8, groove
    # 0.6x1.0" — none of which the plinth has. A summary line that describes a different part than
    # the one on disk is worse than no summary line.
    if style in ("ring", "ring_bevel", "two_step"):
        run, drop = C.ENCODER_RING_BEVEL_RUN, C.ENCODER_RING_BEVEL_DROP
        base = C.ENCODER_RING_TOP_DIA + 2 * run
        wall = C.ENCODER_RING_TOP_DIA / 2 + C.ENCODER_RING_ROOF * run / drop - C._cav_corner_r
        groove = ("none" if style != "ring_bevel"
                  else f"{C.ENCODER_RING_FOOT_GROOVE_D}x{C.ENCODER_RING_FOOT_GROOVE_H}")
        shape = (f"circular collar: top Ø{C.ENCODER_RING_TOP_DIA} base Ø{base:.2f} "
                 f"bevel {run}/{drop} ({_m.degrees(_m.atan(run / drop)):.1f}° from vertical) "
                 f"foot groove {groove} | roof wall over cavity corners {wall:.2f} | "
                 f"shows past the Ø{K.KNOB_OD} knob {(base - K.KNOB_OD) / 2:.2f} all round")
    elif style == "plinth":
        fx, fy = 2 * C._plinth_half_x, 2 * C._plinth_half_y
        bx, by = 2 * C._plinth_foot_half_x, 2 * C._plinth_foot_half_y
        # Quote the FOOT as well as the wall. Reporting only the wall understated the footprint by
        # 2 x the chamfer the moment the foot flare was added — the number a reader cares about is
        # how much deck the bezel actually covers.
        shape = (f"foot {bx:.2f} x {by:.2f} at the deck -{C.ENCODER_PLINTH_TAPER_DEG}° taper-> "
                 f"shoulder {fx:.2f} x {fy:.2f} (plan R{C.ENCODER_PLINTH_CORNER_R}) -> "
                 f"round top Ø{C.ENCODER_PLINTH_TOP_DIA} | cavity steps in at Z"
                 f"{C.ENCODER_PLINTH_STEP_Z:.2f}, morph from Z{C.ENCODER_PLINTH_SHOULDER_Z:.2f} | "
                 f"corner wall {C._plinth_corner_wall:.2f} | "
                 f"shows past the Ø{K.KNOB_OD} knob {(bx - K.KNOB_OD) / 2:.2f} at the flats, "
                 f"{C._plinth_corner_r + C._plinth_taper_flare - K.KNOB_OD / 2:.2f} "
                 f"at the corners (measured at the foot)")
    elif style == "mound":
        shape = (f"ogee plateau: top Z{C.ENCODER_SHELL_TOP_Z:.2f}, "
                 f"foot R{C.ENCODER_BEZEL_FOOT_R} / top R{C.ENCODER_BEZEL_TOP_R}")
    else:
        shape = f"no proud material; aperture Ø{C.ENCODER_APERTURE_DIA}"
    print(f"[{tag}] style={style} | {shape} | "
          f"cover feature top Z={encoder_feature_top_z():.2f} | "
          f"knob hem Z={K.knob_hem_z():.2f}")

    top = build_top_part("right")
    top_stl = OUT / f"{tag}_top.stl"
    if not export_stl(top, str(top_stl)):
        raise RuntimeError(f"export_stl failed for {top_stl}")
    print(f"  wrote {top_stl} ({top_stl.stat().st_size} bytes)")

    if want_knob:
        from sofle_case.encoder_phantom import build_encoder_phantom
        print("  " + K.knob_seating_report())
        # Two encoder states, because the shaft has to be cut for the knob to seat: "enc" is the
        # shaft trimmed to length (the assembly as it will exist), "encraw" the as-bought 20 mm.
        # Pair "enc" with "knob" and "encraw" with "knobdown" — mixing them draws an assembly that
        # cannot be built.
        for name, part in (("knob", K.place_knob()),
                           ("knobdown", K.place_knob(bottomed=True)),
                           ("enc", build_encoder_phantom(with_knob=False)),
                           ("encraw", build_encoder_phantom(with_knob=False, trimmed=False))):
            path = OUT / f"{tag}_{name}.stl"
            if not export_stl(part, str(path)):
                raise RuntimeError(f"export_stl failed for {path}")
            print(f"  wrote {path} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main(sys.argv[1:])
