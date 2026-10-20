<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-18 | Updated: 2026-05-18 -->

# scripts/

## Purpose
Standalone CLI utilities. Two categories: the main build script (runs every time you want STL output) and the one-off PCB parsers (only needed when PCB sources change).

## Key Files

| File | Description |
|------|-------------|
| `build.py` | **Main build CLI.** Builds `build_case_half(side, oled)` and `build_mcu_encoder_cover(side, oled=...)`, exporting `sofle_case_{side}.stl` and `sofle_cover_{side}.stl` to `output/`. `--oled none|long|short` (default `C.OLED_MODE`) is passed explicitly to every builder; non-`none` modes add `_oled-{mode}` to BOTH STL names and print `oled_fit_report`. `--show` opens the viewer; `--phantoms` adds view-only hardware (plus the OLED slab in OLED modes). |
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
  python scripts/build.py right --oled long --show --phantoms   # OLED variant + hardware
  python scripts/build.py left --oled short --out /tmp/x       # *_oled-short.stl + fit report
  ```
- Options: `--oled none|long|short` (default `C.OLED_MODE`), `--out PATH` (default `output`), `--show`, `--phantoms`, `--tolerance` (default 1e-4 mm), `--angular-tolerance` (default 0.01 rad). Keep README's option table in sync when adding one.
- Parse scripts are **one-off**. Do not run them unless PCB hardware changes.
- `build.py` uses `click` for argument parsing. Add new options with `@click.option`.
- Output directory defaults to `output/` and is created automatically.
- STEP export is unsupported and removed. Before each build, `build.py` removes only the requested side's exact known legacy monolithic STEP and split top/bottom artifacts; unrelated output files are preserved.

### Testing Requirements
- `test_build_cli.py` smoke-tests `build.py` by invoking it via subprocess: the case and cover STLs per side, legacy cleanup, the `_oled-{mode}` suffixes, and the pinned OLED fit-report lines (`right --oled long`, `left --oled short`).

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
