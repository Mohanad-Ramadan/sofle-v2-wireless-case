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
| `canopy.py` | MCU bay canopy (S-curve ramp + funnel over the nice!nano) — **fused into `build_top_part`** as part of the tub, not a separate part. Also cuts the roof **puzzle strokes** (`_puzzle_cutter`, `_offset_roofline`, `_roofline_slope`, `canopy_puzzle_region`/`_strokes`). |
| `canopy_puzzle.py` | **Pure plan geometry** for the roof strokes: two straight lines drawn across the ASSEMBLED pair, each crossing both canopies, fitted from the design sketch. Imports `constants` only — the direction is canopy → canopy_puzzle, never the reverse. |
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

14. The canopy roofs carry **puzzle strokes**: two straight lines drawn across the ASSEMBLED pair, each crossing BOTH canopies, so the four strokes are really two lines and the mark completes only when both halves are on the desk. Two properties follow and are both tested. (a) The halves **cannot** look alike — one line meets each canopy at a different angle because they are splayed, so "right must not mirror left" is arithmetic, not a table of tuned numbers (on the right one stroke runs nearly lengthwise, dx/dy ≈ −0.20, while its partner on the left runs across at +1.79). (b) Collinearity across the gap is **exact** (~1e-14 mm), because both strokes are cut from one line rather than aimed at each other; if that number ever becomes merely small, someone has replaced the derivation with transcription. `canopy_puzzle` owns the assembled-frame definition and is **fitted from the design sketch**, not invented — the sketch was measured by pixel classification + PCA + a Hough split, its stroke pairs matched in page space to 0.11°, and one splay plus two lines fit all four strokes to **0.166 mm max / 0.124 rms**. Fitting rather than transcribing was deliberate: the four measured strokes individually imply 48.6° of splay from one pair and 50.8° from the other, so transcribing would bake that 2° disagreement in permanently instead of surfacing it as a residual.

    **The separation is two different things — do not conflate them.** At DESIGN time it is an input that decides where the lines cross each roof; changing it re-places the strokes and collinearity stays exact, with a usable window of about +8 mm before line 0 slides off the right roof (`strokes` then raises rather than emitting nothing). At USE time the grooves are already cut, so misplacing the printed halves breaks each line by the component of that error **perpendicular to itself**: measured 0.81 mm per mm for the steep line (53.9° from horizontal) and 0.04 mm per mm for the near-level one (2.5°). With a 1.6 mm groove that is ±1 mm of tolerance for the steep line and ±18 mm for the level one. Keeping one forgiving line in the pair is deliberate — the effect degrades by half rather than all at once.

    **Where each stroke stops is measured too, not chosen.** The line fit fixes direction and position but says nothing about extent. `PUZZLE_STROKE_COVER` holds the sketch's per-stroke coverage of its own chord across the roof — measured by RANSAC-splitting the white stroke pixels and comparing each stroke's extent with its line's chord clipped against that shape's oriented box. It is stated as a **fraction** on purpose: a ratio along a line is affine-invariant, so it needs no page→mm transform and survives the sketch rectangles' aspect (2.43) differing from the roof strip's (2.60). Measured: left 0 = 1.007, left 1 = 0.666, right 0 = 0.502, right 1 = 1.006 — each half gets one stroke spanning its roof edge-to-edge and one that stops, and the halves differ in which (the same splay-driven asymmetry the angles have). The two below 1.0 are applied (right 0 → 30.7 mm, left 1 → 15.4 mm); the two at ~1.0 are simply the absence of a trim. Trims are anchored at the stroke's NORTH end — the end the sketch has on the shape's edge — so they pull the free terminal back and never the anchored one, and because a trim slides an endpoint ALONG the line, collinearity is untouched: a stroke may stop early, it may not stop somewhere else. The trim is applied LAST, against the broken-out chord, so "half its run" means half of what the stroke actually crosses.

    A stroke **crosses the ramp** (left line 1 — right 0 did too until it was trimmed), which is why `_puzzle_cutter` clips the footprint prism against a **normal-offset** roofline instead of dropping a fixed depth in Z: a vertical drop thins a 0.5 mm groove to 0.40 on the 35.9° ramp, and would pass any "did it cut?" check while going shallow where the surface is most visible. `_offset_roofline`'s slopes must come from `_roofline_slope` (the **analytic** derivative of `_smoothstep`) — a one-sided finite difference at the foot reads the ramp's first 0.06 mm of rise as a slope, pushes the offset endpoint north of `CANOPY_RAMP_FOOT_Y`, and `_yz_prism`'s span filter then drops the south face so the sketch will not close. Depth is derived against `CANOPY_ROOF_WALL − CANOPY_PUZZLE_MIN_ROOF` and asserted at import.

    **Terminals: three kinds, and each end is exactly one of them.** (i) **Gap side** — every stroke runs out to the roof's own edge there, so the continuation across the gap reads as one line instead of two marks pointing at each other. That edge is the **chamfer TOP LINE**, one `canopy_top_chamfer` horizontal leg inboard of the wall (x = `CANOPY_WEST_OUTER_X + h` = 11.7, y = `CANOPY_NORTH_OUTER_Y − h` = 120.3) — the strokes border the facets, they do not cross them. Aiming past the top line at the wall face does not even work: both facets fall away from the swept roofline (2:1 on the west), so the cutter stops biting ~0.25 mm past the arris, and on the way it drags the mark across the NW corner round and up to the USB pocket. (ii) **East** — each half's UPPER stroke additionally breaks THROUGH the east arris (`CANOPY_EAST_X + CANOPY_PUZZLE_EAST_BREAK`); that arris is sharp, no facet, so this is the one edge genuinely notched, once per half. (iii) **Free** — a trimmed stroke's terminal stops in open roof.

    Which stroke is "upper" is DERIVED — `canopy_puzzle.upper_index`, northernmost by midpoint of its **safe-region chord**. It must be answered *before* breaks and trims: breaks lengthen and trims shorten, so a midpoint taken from the finished segments names the other stroke on the right half and would move the east break to the wrong one. That is a real bug that was caught by a test, not a hypothetical.

    One stroke (right 0) is aimed too far north to reach the west line and borders the **north** chamfer instead, which puts its terminal inside the band the north keep-out protects. That break is therefore **conditional**: `canopy_puzzle_strokes` checks `_puzzle_clears_pocket` and falls back to the plain keep-out if the terminal would come within `CANOPY_PUZZLE_POCKET_GAP` of the USB overmold pocket, whose roof budget is `CANOPY_USB_OM_ROOF_MIN` (0.5 mm) — exactly what a groove spends. At the fitted layout it clears by ~4 mm; at other separations it does not, which is why this is checked rather than asserted.

    Ends are **square**, never rounded (`_slot_prism` is a plain box prism): a stroke ends as if a knife lifted off it. A rounded cap reads as a blob on a thin line, worst on exactly the free terminals. `test_no_terminal_is_rounded` asserts the strokes introduce **no** cylindrical face at all, which is stronger than counting caps and needs no bookkeeping about which ends are free. Guarded alongside it: `test_the_east_arris_is_broken_exactly_once` (the notch AND the intactness of the rest of that arris), `test_no_stroke_crosses_a_chamfer_top_line`, and `test_every_stroke_runs_out_at_the_gap_side`. Note `test_canopy_west_top_facet_runs_the_whole_shoulder` builds `puzzle=False`: a stroke terminal at the arris otherwise reads as a broken east edge inside its 2.0 mm window.

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
