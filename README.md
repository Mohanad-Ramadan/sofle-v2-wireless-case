# Sofle V2 Wireless Case

Parametric build123d generator for the Sofle V2 Wireless (Alt_Switch). Each
reversible half is a single surface-less monolithic tray: the rim ends exactly
at the switch-plate top, with integrated tapped bosses, battery/JST recesses,
slide-switch access, and rubber-foot seats.

The nominal PCB-to-inner-wall clearance is **0.40 mm per side**, with **4.75 mm**
structural walls. Printed fit still requires checking against the actual PCB.

## Build

```sh
source .venv/bin/activate
python scripts/build.py left
python scripts/build.py right
```

Each command writes `output/sofle_case_{side}.stl` and the separate removable
`output/sofle_cover_{side}.stl`. STEP export is unsupported and has been removed.
When rebuilding, the CLI removes only the exact known legacy monolithic STEP
and split top/bottom artifacts for the requested side; unrelated files are
preserved. Use `--show` to open the viewer and add
`--phantoms` to include the hardware; phantoms are never fused or exported.

## Test

```sh
ruff check .
pytest tests/ -x -q
```

The authoritative vertical stack and the protected south facet dimensions are
documented in [docs/z-stack.md](docs/z-stack.md) and defined in
`src/sofle_case/constants.py`.

## MCU cover south edge

The removable cover has a **17 mm-wide, 4 mm-deep faceted south recess**,
with a **6 mm flat central lip**, diagonal sides, **1.5 mm clipped outer
corners**, and a **0.5 mm top bevel**. Normally offset cavity facets preserve
the **1.5 mm south wall**; the inner lip remains **0.5 mm clear of the
encoder plate-window envelope**.

Adjust `COVER_RECESS_DEPTH`, `COVER_RECESS_HALF_WIDTH`, and
`COVER_RECESS_FLAT_HALF_WIDTH` in `src/sofle_case/constants.py`.
Reducing depth moves the shoulders inward without moving the central lip
or sacrificing wall thickness or clearance. Both halves mirror the recess.
Physical fit still needs a printed check.

## Slide-switch access

The tray and mounted MCU cover share **one concave, jack-like port** with a
rounded rectangular outline. Its nominal outer rim is 12 × 7.2 mm, with
10 × 6.4 mm clearance at the actuator contact face. The floor and sides curve
continuously into the rear hardware clearance: no flat back-wall ledge,
nested slot, or abrupt second step. The cover roof remains closed.

The unchanged nub phantom represents the entire actuator travel. This port
allows localized fingertip-pad contact, not entry of a whole finger. Tests
use a 5 × 4 mm contact patch with at least 0.3 mm clearance shifting across
that face, plus a separate check that the mounted cover is actually relieved.
Physical pad-only switching and comfort still need a printed-assembly check.
