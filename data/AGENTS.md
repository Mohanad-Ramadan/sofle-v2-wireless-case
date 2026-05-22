<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-18 | Updated: 2026-05-18 -->

# data/

## Purpose
Cached PCB geometry extracted from KiCad sources. These JSON files are the runtime source of truth for PCB shape, mounting hole positions, and component placements. They avoid re-parsing Gerber/CPL files on every build.

## Key Files

| File | Description |
|------|-------------|
| `pcb_outline.json` | Ordered closed polygon of the PCB edge cuts in PCB coords. Loaded by `pcb_geometry.py`. |
| `mounting_holes.json` | 5 PTH mounting hole centers (T9, Ø4.1mm) in PCB coords. Loaded by `pcb_geometry.py`. |
| `components.json` | Component placements: XY position, rotation, reference designator. Used by phantom modules and cutout positioning. |
| `plate_outline.json` | Switch plate edge polygon in PCB coords. Used by `plate_phantom.py`. |
| `plate_cutouts.json` | Switch cutout rectangles for plate phantom. |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `raw/` | Original KiCad source files: Gerber edge cuts (`.gbr`), PTH drill file (`.drl`), component placement CSV (`.csv`). Input to the parse scripts. |

## For AI Agents

### Working In This Directory
- **Never edit JSON files by hand.** Regenerate from `raw/` sources using the parse scripts:
  ```bash
  python scripts/parse_gerber.py data/raw/SofleKeyboard-EdgeCuts.gbr
  python scripts/parse_cpl.py data/raw/CPL-SofleKeyboard.csv
  python scripts/parse_kicad_plate.py data/raw/...
  ```
- Only re-run parsers if the PCB hardware actually changes. For case geometry work, the cached JSON is correct.
- PCB coordinate convention: X right, Y **down** (KiCad). `constants.pcb_to_case()` converts to case coords (Y up).

<!-- MANUAL: -->
