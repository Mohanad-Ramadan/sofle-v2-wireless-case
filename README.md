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

Last verified: 2026-08-14

- Tests: 248 passed, 0 failed
- Typing angle: **7°**, produced by the bottom case being a wedge (1.0 mm thick at the front,
  16.47 mm at the back). Total assembly height 43.12 mm at the back, 26.98 mm at the front.
- The two parts are a sandwich: deep TOP tub + inset BOTTOM plate, joined by a rabbet and
  five screws through the standoffs. Print the matching TOP for each half — they differ in
  height by 2.76 mm because the USB jack sits at a different Z on each.
