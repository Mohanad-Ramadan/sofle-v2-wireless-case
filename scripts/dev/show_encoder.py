"""Open JUST the encoder area in OCP CAD Viewer: TOP part + EC11 + knob, nothing exported.

The viewer must already be running (VS Code: "OCP CAD Viewer: Open viewer", or `python -m
ocp_vscode`). Building only the right TOP part keeps this to one build instead of four.

    python scripts/dev/show_encoder.py                 # current ENCODER_COVER_STYLE
    python scripts/dev/show_encoder.py --style ring    # try another one
    python scripts/dev/show_encoder.py --side left
"""
from __future__ import annotations
import sys

from sofle_case import constants as C


def main(argv: list[str]) -> None:
    side = "right"
    for k, a in enumerate(argv):
        if a == "--style":
            C.ENCODER_COVER_STYLE = argv[k + 1]
        elif a == "--side":
            side = argv[k + 1]

    from sofle_case import knob as K
    from sofle_case.case import build_top_part, encoder_feature_top_z
    from sofle_case.encoder_phantom import build_encoder_phantom

    print(f"style={C.ENCODER_COVER_STYLE} side={side}")
    print(f"  cover feature top Z {encoder_feature_top_z():.2f}")
    print(f"  {K.knob_seating_report()}")

    def _side(part):
        """Phantoms are authored right-handed, like the case; mirror them for a left build."""
        if side != "left":
            return part
        from build123d import Plane, Pos, mirror
        return Pos(C.OUTER_WIDTH / 2, 0, 0) * mirror(
            Pos(-C.OUTER_WIDTH / 2, 0, 0) * part, about=Plane.YZ)

    parts = [build_top_part(side),
             _side(build_encoder_phantom(with_knob=False)),
             _side(K.place_knob()),
             _side(K.place_knob(bottomed=True))]
    names = ["top", "ec11(phantom)", "knob(design seating)", "knob(untrimmed shaft)"]

    sys.path.insert(0, "scripts")          # same trick render_encoder_sheet.py uses
    from viewer_guard import require_live_viewer
    port = require_live_viewer()
    from ocp_vscode import show
    # Colours make the phantoms obviously not-parts; alphas keep the knob from hiding the bezel.
    show(*parts, names=names,
         colors=["#3a6ea5", "#6e6e78", "#d59020", "#d5902060"],
         alphas=[1.0, 0.9, 0.55, 0.25])
    print(f"sent to the OCP viewer on port {port}")


if __name__ == "__main__":
    main(sys.argv[1:])
