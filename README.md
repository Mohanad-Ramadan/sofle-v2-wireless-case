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

Each command writes only `output/sofle_case_left.stl` or
`output/sofle_case_right.stl`. STEP export is unsupported and has been removed.
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
