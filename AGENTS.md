<!-- Generated: 2026-05-18 | Updated: 2026-05-18 -->

# sofle-case — Root

## Purpose
Parametric tray case generator for the Sofle V2 Wireless (Alt_Switch) keyboard. Written in Python using build123d (code-CAD). Produces one STL per half (left / right).

The PCB is reversible, so the two printable case halves are strict mirrors. Each export is one watertight monolithic tray with a flat rim coplanar with the switch plate.

## Key Files

| File | Description |
|------|-------------|
| `AGENTS.md` | AI agent instructions: hardware targets, layout, Z-stack, constants reference, build sequence, known risks |
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
| `output/` | Generated STL files — do not edit manually (see `output/AGENTS.md`) |

## For AI Agents

### Working In This Directory
- **Single source of truth for dimensions:** `src/sofle_case/constants.py`. Edit only there; all derived values recompute at import time.
- **Never edit `data/` JSON by hand.** Re-run `scripts/parse_gerber.py` / `scripts/parse_cpl.py` if the PCB sources change.
- **Always run `pytest` after any change.** All tests must pass before committing.
- The build deliverable is `build_case_half(side)`, exported as `sofle_case_{side}.stl`. Left and right are mirror images with the same volume and footprint.
- STEP export is unsupported and removed. Rebuilding a side removes only its exact known legacy monolithic STEP and split top/bottom artifacts in the requested output directory; unrelated files are preserved.

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
