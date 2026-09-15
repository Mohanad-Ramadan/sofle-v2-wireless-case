<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-18 | Updated: 2026-05-18 -->

# scripts/

## Purpose
Standalone CLI utilities. Two categories: the main build script (runs every time you want STL output) and the one-off PCB parsers (only needed when PCB sources change).

## Key Files

| File | Description |
|------|-------------|
| `build.py` | **Main build CLI.** Builds `build_case_half(side)` and exports one STL to `output/`. `--show` opens the viewer; `--phantoms` adds view-only hardware. |
| `parse_gerber.py` | One-off: parses KiCad Gerber edge-cuts + PTH drill file → writes `data/pcb_outline.json` and `data/mounting_holes.json`. |
| `parse_cpl.py` | One-off: parses KiCad CPL (component placement) CSV → writes `data/components.json`. |
| `parse_kicad_plate.py` | One-off: parses KiCad plate `.kicad_pcb` → `data/plate_outline.json` + `data/plate_cutouts.json`. **Superseded by `parse_plate_gerber.py`** for the real hardware. |
| `parse_plate_gerber.py` | One-off: parses the original Sofle v2 top-plate **gerber** `Edge_Cuts.gbr` → `data/plate_outline.json` + `data/plate_cutouts.json` (authoritative: 29 standard 14 mm MX cutouts + encoder). |

## For AI Agents

### Working In This Directory
- `build.py` is the only script run regularly. Usage:
  ```bash
  python scripts/build.py left
  python scripts/build.py right
  python scripts/build.py left --show   # opens OCP viewer
  ```
- Parse scripts are **one-off**. Do not run them unless PCB hardware changes.
- `build.py` uses `click` for argument parsing. Add new options with `@click.option`.
- Output directory defaults to `output/` and is created automatically.
- STEP export is unsupported and removed. Before each build, `build.py` removes only the requested side's exact known legacy monolithic STEP and split top/bottom artifacts; unrelated output files are preserved.

### Testing Requirements
- `test_build_cli.py` smoke-tests `build.py` by invoking it via subprocess and checking exactly one non-empty STL is written per side.

### Common Patterns
- All scripts use `from __future__ import annotations` and `pathlib.Path` (not `os.path`).

## Dependencies

### Internal
- `src/sofle_case/case.py` — `build_case_half()` entry point

### External
- `click ≥ 8.1` — CLI argument parsing
- `build123d` — `export_stl`
- `ocp-vscode` (optional dev) — `show()`, `save_screenshot()`

<!-- MANUAL: -->
