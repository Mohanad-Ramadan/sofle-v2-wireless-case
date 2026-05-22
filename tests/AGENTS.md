<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-18 | Updated: 2026-05-18 -->

# tests/

## Purpose
pytest suite — 60 tests covering geometry correctness, dimensional fit, manifold integrity, and CLI smoke tests. All tests must pass after every change.

## Key Files

| File | Description |
|------|-------------|
| `test_constants.py` | Sanity-check: envelope ≥ PCB + walls, Z-stack is monotonically increasing |
| `test_tray.py` | Tray shell: outer bbox matches constants, single solid (no floating slab regression), MCU hill flush on −X and +Y walls |
| `test_case.py` | Full case half: bounding box, single solid, volume sanity |
| `test_holes.py` | Standoff XY positions match `data/mounting_holes.json` T9 positions |
| `test_standoff.py` | Stepped standoff geometry: height, lower OD, centering |
| `test_clearances.py` | USB-C and slide-switch cutout edges clear component bodies by ≥ 0.3 mm |
| `test_cutouts.py` | USB-C slot geometry: width, Z range, Y depth |
| `test_manifold.py` | Left and right halves are watertight (no open edges) |
| `test_print_envelope.py` | Each half fits a 250 × 210 mm FDM bed |
| `test_pcb_geometry.py` | PCB polygon loads correctly, `pcb_to_case` transform is accurate |
| `test_pcb_phantom.py` | PCB phantom builds without error |
| `test_plate_phantom.py` | Plate phantom builds without error |
| `test_switch_phantom.py` | Switch phantom builds without error |
| `test_build_cli.py` | `scripts/build.py` invoked via subprocess; STL + STEP written with non-zero size |
| `test_parse_gerber.py` | Gerber/drill parser output matches expected polygon + hole positions |
| `test_parse_cpl.py` | CPL parser extracts correct component positions |

## For AI Agents

### Working In This Directory
- Run with `pytest tests/ -x -q` (fail-fast, quiet). Full suite takes ~15 seconds.
- **Never skip or mock geometry calls** in tests — the geometry must actually build. Tests are the regression guard for the OCC kernel.
- When adding a new constant or feature, add a corresponding test. Minimum: bbox check + single-solid check.
- `test_tray.py::test_tray_is_single_solid` is the most important regression guard — it catches the "floating hill slab" failure mode where the MCU hill detaches from the shell.

### Common Patterns
- Tolerance on float comparisons: `< 0.01` mm (OCC kernel precision).
- Geometry tests call the real build functions (`build_tray()`, `stepped_standoff()`, etc.) — no mocking.
- Phantom tests only check that `.build()` or `build_*_phantom()` runs without exception; they don't assert geometry.

## Dependencies

### Internal
- All `sofle_case.*` modules

### External
- `pytest ≥ 8.0`
- `build123d` (geometry kernel — used directly in tests)

<!-- MANUAL: -->
