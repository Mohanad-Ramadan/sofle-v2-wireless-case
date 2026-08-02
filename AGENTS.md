<!-- Generated: 2026-05-18 | Updated: 2026-05-18 -->

# sofle-case — Root

## Purpose
Parametric tray case generator for the Sofle V2 Wireless (Alt_Switch) keyboard. Written in Python using build123d (code-CAD). Produces one STL + STEP per half (left / right).

The Sofle PCB is reversible, so the BOTTOM plate and the legacy single-piece tray are strict mirrors — one STL serves both halves. **The TOP part is not.** The two builds carry the nice!nano in opposite orientations (`C.MCU_ORIENTATION`: left flipped / components down, right neutral / components up), which puts the USB-C jack at a different Z on each, so the canopy's north-wall port band differs: left 16.84→21.5, right 19.6→24.26 (shell neck) with a 7 mm-tall overmold pocket around each. The canopy ridge is common (26.98), so the silhouette and bounding box still match — only the window moves. Print the matching TOP for each half.

## Key Files

| File | Description |
|------|-------------|
| `AGENT.md` | AI agent instructions: hardware targets, layout, Z-stack, constants reference, build sequence, known risks |
| `README.md` | Human-facing quick-start: build commands, test command, last-verified status |
| `pyproject.toml` | Package metadata, dependencies (`build123d`, `numpy`, `click`), pytest config |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `src/` | Package source — all geometry and constants (see `src/AGENTS.md`) |
| `tests/` | pytest suite covering geometry, fit, manifold (see `tests/AGENTS.md`) |
| `scripts/` | Build CLI and PCB-data parsers (see `scripts/AGENTS.md`) |
| `docs/` | Z-stack reference and design docs (see `docs/AGENTS.md`) |
| `data/` | Cached PCB geometry JSON — source of truth for polygon and hole positions (see `data/AGENTS.md`) |
| `output/` | Generated STL + STEP files — do not edit manually (see `output/AGENTS.md`) |

## For AI Agents

### Working In This Directory
- **Single source of truth for dimensions:** `src/sofle_case/constants.py`. Edit only there; all derived values recompute at import time.
- **Never edit `data/` JSON by hand.** Re-run `scripts/parse_gerber.py` / `scripts/parse_cpl.py` if the PCB sources change.
- **Always run `pytest` after any change.** All tests must pass before committing.
- The build deliverables are the two sandwich parts per side — `build_top_part(side)` (deep TOP tub) and `build_bottom_part(side)` (inset BOTTOM plate) — joined by a rabbet and screwed through the standoffs. `build_case_half` is the legacy single-piece tray. Left and right are mirror images with the same volume and footprint; `side` mirrors the geometry (and sets the output filename).

### Testing Requirements
```bash
source .venv/bin/activate
pytest tests/ -x -q
```

### Common Patterns
- All Z coordinates measured from `Z = 0` (case outer bottom face).
- PCB coordinates use the KiCad convention (Y increases downward). `pcb_to_case(x, y)` in `constants.py` converts to case coords (Y increases upward, origin at outer lower-left corner).
- Every geometry module has an `if __name__ == "__main__":` viewer block using `ocp_vscode.show()`. Keep that import **inside** the block so it stays an optional dev dependency.

## Dependencies

### External
- `build123d ≥ 0.7.0` — code-CAD geometry kernel (wraps OpenCASCADE via OCP)
- `numpy ≥ 1.26` — array ops in parsers
- `click ≥ 8.1` — CLI for `scripts/build.py`
- `pytest ≥ 8.0` (dev) — test runner
- `ocp-vscode ≥ 2.0` (dev, optional) — CAD viewer integration

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
