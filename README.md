# Sofle V2 Wireless Case

Parametric build123d generator for the Sofle V2 Wireless (Alt_Switch). Each
reversible half is a single surface-less monolithic tray: the rim ends exactly
at the switch-plate top, with integrated tapped bosses, battery/JST recesses,
slide-switch access, and rubber-foot seats.

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
