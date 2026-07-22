<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-18 | Updated: 2026-07-22 -->

# src/sofle_case/

## Purpose
The core `sofle_case` Python package. Contains all parametric geometry (tray shell, standoffs, battery pocket, switch-plate membrane, MCU canopy, encoder plateau), constants, PCB data loading, and phantom visualisation helpers. The primary entry points are `case.py::build_top_part(side)` and `build_bottom_part(side)` — the two printable halves of the **sandwich clamshell** (a deep TOP tub + an inset BOTTOM plate that join via a **rabbet**, screwed together through the standoffs). `build_case_half()` is the legacy single-piece tray.

## Key Files

| File | Description |
|------|-------------|
| `constants.py` | **Single source of truth for all dimensions.** Every Z height, wall thickness, clearance, cutout size, and component position lives here. Edit here first; everything else recomputes. |
| `case.py` | Top-level composer + sandwich split. `build_top_part(side)` = deep tub (full-height `build_tray` − `_plate_pocket`) with the membrane / encoder plateau / canopy fused on and the slide-switch cuts subtracted; `build_bottom_part(side)` = inset floor plate (`_plate_envelope`) + standoffs − battery pocket. Rabbet helpers: `_plate_pocket`, `_chamfer_pocket_mouth`. `_mirror_left`/`_heal` build the left half; `build_case_half` is the legacy single-piece tray. Also `_encoder_shell`, `_slide_scoop`, `_slide_actuator_cavity`, `_corner_markers`. |
| `tray.py` | Outer shell + inner cavity, walls flat at `rim_z` (default `MAIN_RIM_Z`; the sandwich tub passes `COVER_TOP_Z`). +Y B+/B- relief bump + fillets/chamfers + the `offset_extruded` polygon helper (shared with the rabbet). Most-edited file. No MCU hill (the canopy is fused in `case.py`). |
| `standoffs.py` | Stepped standoff: lower shoulder (Ø5.5mm `STANDOFF_OD_LOWER`) + upper pin (Ø3.9mm `STANDOFF_OD_UPPER`) + M2 tap bore (Ø1.8mm) + 0.3mm entry chamfer. |
| `battery.py` | Battery pocket cutter: blind recess in the floor for a 405070 LiPo cell, subtracted in `build_bottom_part`. |
| `canopy.py` | MCU bay canopy (S-curve ramp + funnel over the nice!nano) — **fused into `build_top_part`** as part of the tub, not a separate part. |
| `pcb_geometry.py` | Loads `data/pcb_outline.json`, `data/mounting_holes.json`, `data/components.json`; `pcb_to_case()` transform + `slide_switch_placement`/`rotate_2d`. |
| `top_cover.py` | **Switch-plate membrane.** Thin (`COVER_THICKNESS`) plate-shaped lid with ~16.5 mm windows clearing the 15.6 mm MX housings + standoff screw holes; MCU/OLED bay open via the plate notch. Built via `build_top_cover()` and **fused into `build_top_part`** as the tub ceiling (not exported separately). |
| `pcb_phantom.py` | Visual phantom: main PCB + nice!nano MCU + slide switch body. For OCP viewer only. |
| `plate_phantom.py` | Visual phantom: switch plate (from `data/plate_*.json`, re-parsed from the v2 top-plate gerber). For OCP viewer only. |
| `switch_phantom.py` | Visual phantom: Cherry MX switch solids at every switch position. For OCP viewer only. |
| `__init__.py` | Empty package marker. |

## For AI Agents

### Working In This Directory

**Before touching any file, read `constants.py` first.** All geometry is driven by constants — never hardcode a dimension inline.

Key invariants to preserve:
1. `PCB_TOP_Z == PCB_SEAT_Z + 1.6` — derived, do not break.
2. `PLATE_TOP_Z == PLATE_SEAT_Z + 1.6` — derived, do not break.
3. `MAIN_RIM_Z == PLATE_TOP_Z` — minimal short case: the tray walls end flush with the plate top, no hill. (The canopy + encoder plateau rise above this, but they are fused on in `case.py`, not part of `tray.py`.)
4. `tray.py` must produce **exactly 1 solid** — `test_tray_is_single_solid` guards this. Both sandwich parts (`build_top_part`/`build_bottom_part`) must also each be a single valid solid — `test_split_parts_are_valid_single_solids`.
5. No wall rises above the tray's `rim_z` (default `MAIN_RIM_Z`; the sandwich tub deliberately passes `COVER_TOP_Z`) — `test_no_wall_above_rim` guards the default flat-wall tray.
6. Rabbet fit is set by `SEAM_FIT_CLEAR`/`SEAM_LEDGE_CLEAR` (0.3 mm) — the parts nest with clearance (zero interference); the screws + standoffs, not the rabbet, set the clamp and precise registration.

**Phantom modules** (`pcb_phantom.py`, `plate_phantom.py`, `switch_phantom.py`) are visual only. They must not be imported by structural modules. Guard all phantom imports inside `if __name__ == "__main__":` blocks.

### Testing Requirements
```bash
source .venv/bin/activate
pytest tests/ -x -q
```
All tests must pass. Geometry tests call real build functions — no mocking.

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
- Empirical constants in `constants.py` are geometry-tuned — change with care and re-run tests.

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
