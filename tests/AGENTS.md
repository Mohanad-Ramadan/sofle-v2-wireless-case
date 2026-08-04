<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-18 | Updated: 2026-05-18 -->

# tests/

## Purpose
pytest suite covering geometry correctness, dimensional fit, manifold integrity, and CLI smoke tests. All tests must pass after every change.

## Key Files

| File | Description |
|------|-------------|
| `shared_builds.py` | Session-cached wrappers for the expensive OCC builders — tests import `build_*` from here, never from `sofle_case.*` |
| `test_constants.py` | Sanity-check: envelope ≥ PCB + walls, Z-stack is monotonically increasing |
| `test_tray.py` | Tray shell: outer bbox matches constants (flat walls at `MAIN_RIM_Z`), single solid (no floating-relief regression) |
| `test_case.py` | Full case half: bounding box, single solid, volume sanity |
| `test_holes.py` | Standoff XY positions match `data/mounting_holes.json` T9 positions |
| `test_standoff.py` | Stepped standoff geometry: height, lower OD, centering |
| `test_clearances.py` | Slide-switch slot fit; flat-wall (no-hill) guarantees; +Y relief clears component bodies |
| `test_cutouts.py` | Slide-switch wall cutters build as valid parts |
| `test_manifold.py` | Left and right halves are watertight (no open edges) |
| `test_print_envelope.py` | Each half fits a 250 × 210 mm FDM bed |
| `test_pcb_geometry.py` | PCB polygon loads correctly, `pcb_to_case` transform is accurate |
| `test_pcb_phantom.py` | PCB phantom builds without error |
| `test_plate_phantom.py` | Plate phantom builds without error |
| `test_top_cover.py` | Sandwich lid: single solid, sits on plate top, footprint matches plate, windows clear all switch housings, keycap headroom, screw holes open |
| `test_switch_phantom.py` | Switch phantom builds without error |
| `test_build_cli.py` | `scripts/build.py` invoked via subprocess; STL + STEP written with non-zero size |
| `test_parse_gerber.py` | Gerber/drill parser output matches expected polygon + hole positions |
| `test_parse_cpl.py` | CPL parser extracts correct component positions |

## For AI Agents

### Working In This Directory
- Run with `pytest tests/ -x -q` (fail-fast, quiet). Full suite takes ~55 seconds; `pytest tests/ -n 2 --dist loadfile` finishes in ~40 (xdist workers each load the OCP kernel, so total RAM roughly doubles per worker — keep the count low on memory-tight machines).
- **Import builders from `tests/shared_builds.py`, never directly from `sofle_case.*`.** The module caches each expensive OCC build once per process; peak memory no longer grows with test count. Parts are shared read-only — probes must keep using boolean ops that return new objects (no `-=`/`+=` on a built part).
- **Exception:** a test that monkeypatches a constant (e.g. `COVER_PULLER_NOTCH`) must build FRESH from the real `sofle_case.*` builder inside that test — the cache would otherwise serve geometry built with the shipped default, and a cached build must never be polluted by patched state.
- **Never skip or mock geometry calls** in tests — the geometry must actually build. Tests are the regression guard for the OCC kernel.
- When adding a new constant or feature, add a corresponding test. Minimum: bbox check + single-solid check.
- `test_tray.py::test_tray_is_single_solid` is the most important regression guard — it catches the "floating slab" failure mode where the +Y relief bump detaches from the shell.

### Common Patterns
- Tolerance on float comparisons: `< 0.01` mm (OCC kernel precision).
- Geometry tests call the real build functions via `tests/shared_builds` (`build_tray()`, `build_top_part()`, etc.) — no mocking.
- Phantom tests only check that `.build()` or `build_*_phantom()` runs without exception; they don't assert geometry.

## Dependencies

### Internal
- All `sofle_case.*` modules

### External
- `pytest ≥ 8.0`
- `pytest-xdist ≥ 3.5` (optional parallelism — see run note above)
- `build123d` (geometry kernel — used directly in tests)

<!-- MANUAL: -->
