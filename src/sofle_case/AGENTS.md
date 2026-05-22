<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-18 | Updated: 2026-05-18 -->

# src/sofle_case/

## Purpose
The core `sofle_case` Python package. Contains all parametric geometry (tray shell, standoffs, cutouts), constants, PCB data loading, and phantom visualisation helpers. Entry point is `case.py::build_case_half()`.

## Key Files

| File | Description |
|------|-------------|
| `constants.py` | **Single source of truth for all dimensions.** Every Z height, wall thickness, clearance, cutout size, and component position lives here. Edit here first; everything else recomputes. |
| `case.py` | Top-level composer: `build_case_half(side)` → tray + standoffs − USB-C cutout. Also contains `_corner_markers()` debug helper. |
| `tray.py` | Outer shell + inner cavity + MCU hill (−X and +Y walls) + S-curve cutters + fillets. Most-edited file. |
| `standoffs.py` | Stepped standoff: lower shoulder (Ø5.5mm) + upper pin (Ø3.5mm) + M2 tap bore (Ø1.8mm) + 0.3mm entry chamfer. |
| `cutouts.py` | USB-C open-top slot through +Y wall. Rounded-rectangle profile with side bulge arcs. |
| `pcb_geometry.py` | Loads `data/pcb_outline.json` and `data/mounting_holes.json`; applies `pcb_to_case()` transform. |
| `pcb_phantom.py` | Visual phantom: main PCB + nice!nano MCU + slide switch body. For OCP viewer only. |
| `plate_phantom.py` | Visual phantom: switch plate. For OCP viewer only. |
| `switch_phantom.py` | Visual phantom: Cherry MX switch solids at every switch position. For OCP viewer only. |
| `__init__.py` | Empty package marker. |

## For AI Agents

### Working In This Directory

**Before touching any file, read `constants.py` first.** All geometry is driven by constants — never hardcode a dimension inline.

Key invariants to preserve:
1. `PCB_TOP_Z == PCB_SEAT_Z + 1.6` — derived, do not break.
2. `PLATE_TOP_Z == PLATE_SEAT_Z + 1.6` — derived, do not break.
3. `MCU_HILL_Z == PCB_TOP_Z + 11.0` — MCU + socket + header clearance.
4. `tray.py` must produce **exactly 1 solid** — `test_tray_is_single_solid` guards this.
5. The MCU hill outer face must be **flush** with the shell (same polygon-offset profile) — `test_hill_outer_face_flush_with_shell` guards this.

**Phantom modules** (`pcb_phantom.py`, `plate_phantom.py`, `switch_phantom.py`) are visual only. They must not be imported by structural modules. Guard all phantom imports inside `if __name__ == "__main__":` blocks.

### Testing Requirements
```bash
source .venv/bin/activate
pytest tests/ -x -q
```
All 60 tests must pass. Geometry tests call real build functions — no mocking.

### Common Patterns

**build123d style:**
```python
from build123d import Part, BuildPart, Cylinder, Mode, Locations
from . import constants as C

def my_feature(at: tuple[float, float]) -> Part:
    x, y = at
    with BuildPart() as bp:
        with Locations((x, y, some_z)):
            Cylinder(radius=C.SOME_DIA / 2, height=C.SOME_H)
    assert bp.part is not None
    return bp.part
```

**Coordinate systems:**
- Case coords: origin at outer lower-left corner, Z=0 at outer bottom face.
- PCB coords: KiCad convention (Y down). Use `C.pcb_to_case(x, y)` to convert.
- Spline scalars in `constants.py` (e.g. `S_CURVE_RAMP_MINUS_Y_SCALARS`) are empirically tuned — change with care and re-run tests.

**OCP viewer block (required on every geometry module):**
```python
if __name__ == "__main__":
    from ocp_vscode import show
    show(my_feature(...), names=["my_feature"])
```

## Dependencies

### Internal
- `data/pcb_outline.json`, `data/mounting_holes.json`, `data/components.json` — loaded at call time via `pcb_geometry.py`

### External
- `build123d ≥ 0.7.0` — geometry kernel
- `numpy` — used in parsers
- `ocp-vscode` (optional dev) — viewer only, never imported at module level

<!-- MANUAL: -->
