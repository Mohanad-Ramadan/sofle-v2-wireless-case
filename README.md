# Sofle V2 Wireless Case

Parametric tray case generator for the Sofle V2 Wireless (Alt_Switch) keyboard.

## Build

```
python -m venv .venv && source .venv/bin/activate
pip install -e .[dev]

# One-off: extract dimensions from PCB sources
python scripts/parse_gerber.py /path/to/GERBER-SofleKeyboard.zip
python scripts/parse_cpl.py /path/to/CPL-SofleKeyboard.csv

# Build case halves
python scripts/build.py left
python scripts/build.py right
```

Outputs: `output/sofle_{left,right}_{top,bottom}.{stl,step}` — two parts per half.

## Test

```
pytest
```

## Status

Last verified: 2026-08-16

- Tests: 284 passed, 0 failed
- The north bay is bounded by **one plane**, `BAY_NORTH_INNER_Y` = 118.75 — the tray cavity,
  the ceiling band and the canopy's north wall all land on it, so nothing steps inboard and
  the nice!nano slides in past a single flat wall (1.57 mm clear at the board, 0.57 mm at the
  USB-C jack).
- Typing angle: **6°**, produced by the bottom case being a wedge (1.0 mm thick at the front,
  14.24 mm at the back).
- Overall assembly height **41.17 mm** on the right half — from the canopy ridge at Z = +26.98
  down to the wedge's deepest point at Z = −14.19. The left half is 2.76 mm shorter because the
  USB jack sits at a different Z on each; print the matching TOP for each side.
- The two parts are a sandwich: deep TOP tub + inset BOTTOM plate, joined by a rabbet and
  five screws through the standoffs.
- The visible parting line sweeps up from y ≈ 55, crests around y ≈ 85, and falls to the back
  edge. Below it the bottom case is **flush** with the top — both are extruded from the same
  sectioned outline, so the two silhouettes agree to ~3e-14 mm rather than to a tolerance. The
  gap between them is a constant 2.0 mm reveal.
