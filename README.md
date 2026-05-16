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

Outputs: `output/sofle_case_{left,right}.{stl,step}`

## Test

```
pytest
```

## Status

Last verified: 2026-05-16

- Tests: 60 passed, 0 failed
