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
6. Rabbet fit is set by `SEAM_FIT_CLEAR` (0.2 mm XY) / `SEAM_LEDGE_CLEAR` (0.3 mm Z) — the parts nest with clearance (zero interference); the screws + standoffs, not the rabbet, set the clamp and precise registration.
7. The nano's Y extent comes from `MCU_BODY_N_Y` / `MCU_BODY_S_Y`, **never** `MCU_POS ± MCU_BODY_L/2`. `MCU_POS` is the pin-array centre, and the board is anchored at its USB end — a longer board grows southward. Centring it instead drives the USB jack into the canopy's north wall. Guarded by `test_mcu_board_is_anchored_to_its_pin_array_not_centred_on_it` and `test_usb_jack_stops_short_of_the_north_wall`.
8. The USB-C jack is **mid-mount** (`USB_JACK_H` 3.16 / `USB_JACK_SINK` 1.00): it straddles the nano board, so both jack bands derive from the board faces and differ per orientation. Never model it as a top-mount part sitting on the board.
9. The USB port is a **stepped bore** — overmold pocket (`CANOPY_USB_OM_*`) outside, shell neck (`CANOPY_USB_W` / `canopy_usb_z`) inside — because the jack mouth sits 4.41 mm behind the outer face and a straight hole gives 34% shell engagement while blocking the overmold. Probe each section at its own depth; a mid-wall Y lands inside the pocket.
10. The canopy ridge is derived **per half** via `canopy_ridge_top_z(side)` — never assume a shared height. `CANOPY_RIDGE_TOP_Z` still exists as `max(canopy_ridge_top_z(s) for s in ("left","right"))`, but it is a trap for anything that cares which half it's building; the only legitimate use is `case._slide_scoop`'s cut ceiling, where over-reaching on the shorter half is harmless. Each half's pocket must clear `CANOPY_NORTH_ROUND_R` against its OWN ridge — `test_usb_pocket_stays_buried_under_the_north_shoulder[side]`. `_canopy_roof_z` and `_roofline` take `z_ridge` with **no default**, on purpose: a caller that forgets to pass the per-half ridge silently samples the wrong half's roof surface.
11. `CANOPY_RAMP_SAMPLES` is **25, and that is a CEILING — do not raise it.** Too low rings (9 overshot the analytic smoothstep by 0.14 mm while still passing the monotonicity test, which does not check flatness); too high detonates the mesh, because OCC tessellates by **curvature**, not deviation, and a denser interpolating spline trades deviation for high-frequency curvature wiggle. Measured on the right half: 28k triangles at 9, 39k at 25, 216k at 41, **397k at 51** — a 2.5 MB → 39.9 MB STL to buy 0.023 mm of flatness already 10× under a 0.2 mm layer. The left half never blows up (its ramp is 2.76 mm shorter, so mild curvature), so **measure the RIGHT half**. `test_canopy_ramp_mesh_does_not_detonate` bounds this; nothing caught the 51 regression because every geometric assertion passed — the shape was fine, only the mesh was absurd.
12. The canopy's west top shoulder facet is a **swept boolean** (`_chamfer_west_top`), never a 3-D edge `chamfer()`. OCC rejects an edge chamfer on that run once the ramp `Spline` carries more than ~9 control points, and the old `_round_west_top_edges` swallowed the failure with a bare `return part` — so raising `CANOPY_RAMP_SAMPLES` to 51 silently deleted the facet, and no test caught it. The boolean ruled-lofts a cutter from the body's own roofline, so it is density-independent (verified at 9/13/21/51/81) and it **asserts** that it removed material. `chamfer_v` is the vertical leg, `chamfer_h` the inboard one — explicit now, because the old 3-D call let OCC pick and it picked the reverse.
13. The canopy's NW top corner is a **cylindrical round** (`_round_nw_corner`) at the case's own corner radius. It was briefly a flat diagonal chamfer to escape a measured 64.7° kink (OCC patching the seam with CONE/BSPLINE surfaces); that kink was real but **misattributed** — it only appeared because the west shoulder facet above was silently missing, leaving the cylinder to meet a raw square shoulder. With the facet cut, the corner is exactly one `CYLINDER` face. `test_canopy_nw_corner_is_rounded` pins `kinds == ["CYLINDER"]` on both halves. Lesson: before redesigning a feature to fix a seam artifact, confirm its *neighbours* are actually being built.

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
