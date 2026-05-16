# Sofle V2 Wireless — 3D-Printed Tray Case

**Target hardware:** Sofle V2 Wireless PCB (Alt_Switch variant), nice!nano MCU, MX hot-swap switches, EC11 rotary encoder (H20mm shaft), 0.91" OLED, internal LiPo battery.  
**Modeling tool:** Build123d (Python, code-CAD).  
**Output:** STL + STEP files, one tray per half (left + mirrored right).

All dimensions live in `src/sofle_case/constants.py`. Change there; rebuild with `python scripts/build.py {left,right}`. Run `pytest` after every change.

PCB-derived data is cached as JSON in `data/`. Re-run `scripts/parse_gerber.py` only if the PCB sources change.

Build sequence: see `src/sofle_case/case.py::build_case_half`.

---

## Project Layout

```
sofle_v2_wireless_case/
├── pyproject.toml
├── AGENT.md                    # this file
├── README.md
├── docs/
│   └── z-stack.md              # vertical layer reference with cross-section diagram
├── src/sofle_case/
│   ├── __init__.py
│   ├── constants.py            # all dimensions; SINGLE source of truth
│   ├── pcb_geometry.py         # loads cached PCB polygon JSON
│   ├── tray.py                 # outer shell + cavity + MCU hill + −X wall S-curve cutters + fillet
│   ├── standoffs.py            # stepped standoff with M2 tap
│   ├── cutouts.py              # USB-C open-top slot
│   ├── case.py                 # composes everything; entry point
│   ├── pcb_phantom.py          # PCB + MCU + slide-switch visual for OCP viewer
│   ├── plate_phantom.py        # switch plate visual for OCP viewer
│   └── switch_phantom.py       # MX switch solids for OCP viewer
├── scripts/
│   ├── build.py                # CLI: builds part, exports STL + STEP
│   └── parse_gerber.py         # one-off: extract dimensions from GERBER
├── data/
│   ├── pcb_outline.json        # cached PCB polygon
│   ├── mounting_holes.json     # cached mount positions
│   └── components.json         # component placements (XY, rotation); read by phantoms and cutters
└── tests/
    ├── test_constants.py       # sanity-check dimensions
    ├── test_tray.py            # tray shell + hill geometry
    ├── test_case.py            # full case half (bbox, single solid)
    ├── test_holes.py           # standoff positions match GERBER T9 positions
    ├── test_clearances.py      # cutout alignment and Z clearances
    ├── test_cutouts.py         # USB-C and wall cutter geometry
    ├── test_manifold.py        # watertight mesh check
    ├── test_standoff.py        # stepped standoff geometry
    ├── test_pcb_geometry.py    # polygon load + transform
    ├── test_pcb_phantom.py     # PCB phantom builds without error
    ├── test_plate_phantom.py   # plate phantom builds without error
    ├── test_switch_phantom.py  # switch phantom builds without error
    ├── test_print_envelope.py  # bounding box fits print bed
    ├── test_build_cli.py       # smoke-test scripts/build.py; checks STL + STEP output
    ├── test_parse_gerber.py    # GERBER/drill parser
    └── test_parse_cpl.py       # CPL parser
```

---

## Source Data

### PCB Outline — from `SofleKeyboard-EdgeCuts.gbr`

Bounding box: **143.5 mm wide × 115.5 mm deep**
- X range: −8.5 to 135.0 mm
- Y range: −110.5 to 5.0 mm

Irregular closed polygon with stepped top edge (OLED/encoder bumps) and sloped thumb-cluster cutout in bottom-left. Parsed at build time from cached JSON.

### Case Mounting Holes — from `SofleKeyboard-PTH.drl` (T9, Ø4.1mm)

5 positions in PCB coordinates:

| # | X (mm) | Y (mm) |
|---|--------|--------|
| 1 | 14.07 | −80.26 |
| 2 | 39.57 | −19.05 |
| 3 | 39.57 | −56.96 |
| 4 | 116.07 | −25.66 |
| 5 | 116.07 | −63.96 |

Standoffs pass through with 0.30 mm radial clearance.

### Component Placements

| Component | Designator | Position (mm) | Layer | Notes |
|-----------|-----------|---------------|-------|-------|
| MCU (nice!nano) | U1 | (10.27, −16.16) | top | Body ≈ 18×33mm; USB-C exits +Y edge |
| Slide switch SK12D07VG3 | SW31 | (2.945, −45.23) | top | Actuator nub extends −X; 270° rotation in components.json |
| Reset button (TVBP06) | RSW1 | (7.72, −45.35) | top | Side-actuated; stem points −X |
| Rotary encoder (EC11 H20) | SW25 | (9.47, −65.95) | top | 20mm shaft, knob above |
| OLED socket | J3 | (5.22, −33.69) | top | 5-pin 2.54mm vertical |

---

## Vertical Layer Stack (bottom → top)

```
Z =  0.0  ─── case bottom
Z =  2.0  ─── floor interior top       (FLOOR_THICKNESS)
Z =  2.0–4.5 ─── air gap
Z =  4.5  ─── PCB bottom               (PCB_SEAT_Z)
Z =  6.1  ─── PCB top                  (PCB_TOP_Z = PCB_SEAT_Z + 1.6 mm)
Z = 12.0  ─── nice!nano PCB top        (MCU_PCB_TOP_Z, includes socket height)
Z =  9.1  ─── switch plate bottom      (PLATE_SEAT_Z)
Z = 10.7  ─── switch plate top         (PLATE_TOP_Z)
Z = 14.0  ─── main case wall rim       (MAIN_RIM_Z)
Z = 17.1  ─── MCU hill plateau on −X and +Y walls at MCU corner (MCU_HILL_Z = PCB_TOP_Z + 11.0 mm)
Z = 18.0  ─── USB-C jack body top      (USB_C_BODY_TOP_Z)
```

The −X and +Y walls share a raised plateau (MCU_HILL_Z = 17.1 mm) over the MCU region.
On the −X wall: flat at `MCU_HILL_Z` above the MCU body extent, then a spline descent (S-curve) landing at `MAIN_RIM_Z` below the slide-switch centre, then back up through the switch region.
On the +Y wall: flat at `MCU_HILL_Z` from the −X corner to the MCU +X edge, then a spline descent back to `MAIN_RIM_Z` beyond the MCU footprint.

---

## Key Constants (from `constants.py`)

### Heights
- `FLOOR_THICKNESS = 2.0`
- `PCB_SEAT_Z = 4.5`
- `PLATE_SEAT_Z = 9.1`
- `MAIN_RIM_Z = 14.0`
- `PCB_TOP_Z = 6.1` (PCB_SEAT_Z + 1.6 mm PCB thickness)
- `PLATE_TOP_Z = 10.7` (PLATE_SEAT_Z + 1.6 mm plate thickness)
- `MCU_PCB_TOP_Z = 12` (nice!nano PCB top including socket height)
- `USB_C_BODY_TOP_Z = 18` (USB-C jack body top)
- `MCU_HILL_Z = 17.1` (PCB_TOP_Z + 11.0 mm — wall plateau height above MCU)
- `MCU_BODY_L = 33.0` (nice!nano body length in Y, drives −X wall plateau extent)
- `MCU_BODY_W = 18.0` (nice!nano body width in X, drives +Y wall plateau extent)
- `MCU_HILL_PLUS_Y_REACH_X ≈ 30.77` (case X of MCU +X edge; +Y wall hill ends here)
- `MCU_HILL_PLUS_Y_RAMP_RUN = 8.0` (mm; +Y wall spline descent run from MCU +X edge to MAIN_RIM_Z)
- `MCU_HILL_NEG_X_INNER_BOUND_X = 13.0` (L-mask: keep hill ring at X ≤ this on −X wall)
- `MCU_HILL_NEG_X_SOUTH_Y = 75.0` (south boundary of −X hill strip; S-curve ramp starts here)
- `MCU_HILL_PLUS_Y_INNER_BOUND_Y = 112.5` (L-mask: keep hill ring at Y ≥ this on +Y wall)
- `MCU_HILL_DESCENT_SCALARS = (1.5, 1.5)` (+Y wall spline descent tangent scalars)

### Outer Envelope
- `OUTER_WIDTH = 149.5` (PCB 143.5 + 3.0 mm border each side)
- `OUTER_DEPTH = 121.5` (PCB 115.5 + 3.0 mm border each side)
- `WALL_THICKNESS = 2.5`
- `CORNER_RADIUS = 3.5`
- `TOP_CHAMFER = 0.8`

### Standoffs
- `STANDOFF_OD_LOWER = 5.5` (PCB seat shoulder)
- `STANDOFF_OD_UPPER = 3.5` (passes through PCB Ø4.1 hole)
- `STANDOFF_TAP_DIA = 1.6` (M2 self-tap bore)
- `STANDOFF_TAP_DEPTH = 4.0`

### Clearances
- `PCB_XY_CLEARANCE = 0.5`
- `PCB_HOLE_DIA = 4.1`

### Cutouts
- `USB_C_W = 9.0` — slot width along +Y wall (X axis)
- `USB_C_Z_RANGE = (11, PCB_TOP_Z + 11.5)` = (11, 17.6) — open-top slot; bottom clears jack lower lip, top punches past MCU hill rim
- `USB_C_SIDE_BULGE = 1.5` — outward arc bulge at midpoint of each X-side (rounded rectangle profile)
- `SLIDE_SWITCH_W = 6.0` — switch slot narrow width
- `SLIDE_SWITCH_Z_RANGE = (10, MAIN_RIM_Z + 0.5)` = (10, 14.5) — open-top; bottom clears switch metal body top, top punches past rim
- `S_CURVE_RAMP_Y_START = 31.0` — −Y spline ramp south start in case Y coords
- `S_CURVE_RAMP_MINUS_Y_SCALARS = (2.0, 1.5)` — −Y spline tangent scalars (start, end); tuning knob for ramp shape
- `S_CURVE_RAMP_PLUS_Y_SCALARS = (1.0, 1.0)` — +Y spline tangent scalars

### Component Positions (PCB coords)
- `MCU_POS = (10.27, -16.16)`
- `SW_SLIDE_POS = (2.945, -45.23)` — footprint origin; nub centre offset handled in phantom via 270° rotation
- `SW_RESET_POS = (7.72, -45.35)`
- `SW_ENCODER_POS = (9.47, -65.95)`
- `J_OLED_POS = (5.22, -33.69)`

### Coordinate Transform
`pcb_to_case(x, y)` translates PCB coordinates to case (outer-rect) coordinates.
- `PCB_OFFSET_X = (OUTER_WIDTH - (PCB_X_MAX - PCB_X_MIN)) / 2 - PCB_X_MIN` ≈ 11.5
- `PCB_OFFSET_Y = (OUTER_DEPTH - (PCB_Y_MAX - PCB_Y_MIN)) / 2 - PCB_Y_MIN` ≈ 113.5

---

## Build Sequence (`case.py::build_case_half`)

1. `tray.py::build_tray`:
   a. Build outer shell (PCB polygon offset by WALL_THICKNESS + PCB_XY_CLEARANCE), extrude to MAIN_RIM_Z
   b. Subtract inner cavity (PCB polygon + PCB_XY_CLEARANCE), extruded from FLOOR_THICKNESS upward
   c. Fuse MCU hill solid — wall ring MAIN_RIM_Z→MCU_HILL_Z restricted to the L-corner over MCU; outer/inner faces share the polygon-offset shell faces so the hill is one continuous solid
   d. Apply −X wall S-curve cutters (`_neg_x_wall_cutter_plus_y`, `_neg_x_wall_cutter_minus_y`) — YZ-profile solids subtracted from the −X wall, carving the wall height from MAIN_RIM_Z down to switch level and back up to MCU_HILL_Z
   e. Three-phase fillet: S-curve ramp edges at TOP_CHAMFER (0.8 mm), +Y descent edges at TOP_CHAMFER, flat rim/hill edges at max(TOP_CHAMFER, 0.75×TOP_CHAMFER) depending on OCC geometry constraints
   f. Fillet concave outer-wall notch edges
2. Add 5 stepped standoffs at mounting-hole positions
3. Subtract USB-C open-top slot in +Y wall (punches through raised hill past rim)
4. Single STL serves both halves — PCB is reversible. `build_case_half("left")` and `build_case_half("right")` return identical geometry; the parameter only affects export filename.

---

## Cutout Details

### Slide Switch (SK12D07VG3)
- **Wall:** −X wall
- **Implementation:** Two YZ-profile cutters in `tray.py` (`_neg_x_wall_cutter_plus_y`, `_neg_x_wall_cutter_minus_y`), not a shape in `cutouts.py`
- **Shape:** S-curve — the wall descends from MAIN_RIM_Z via a spline to `z_bot = SLIDE_SWITCH_Z_RANGE[0] − SLIDE_SWITCH_W/2` = 7.0 mm at the switch centre Y, then rises back up to MCU_HILL_Z. The opening is the material removed between the outer wall face and the spline boundary.
- **Switch nub centre:** case Y ≈ 68.3 mm (PCB Y = −45.23 mm, 270° rotation offset applied)
- **Z range:** (10, 14.5) — open top; bottom is 1.5 mm below switch metal body top
- **Depth (X):** cutters extrude from X = −1 to X = MCU_HILL_NEG_X_INNER_BOUND_X + 1 = 14 mm

### USB-C Port
- **Wall:** +Y outer wall
- **Center X:** PCB X = 10.27 mm (case X ≈ 21.8). Both halves share this X — Sofle PCB is reversible, so a single STL serves left and right.
- **Width (X):** 9.0 mm + 2×1.5 mm side bulge = 12 mm outer opening
- **Z range:** (11, 17.6) — open-top slot. Bottom clears the jack lower lip; top punches past MCU_HILL_Z.
- **Y depth:** 31 mm inward from outer wall face. The slot must reach past the MCU's +Y body edge into the empty cavity so the cable path is unobstructed.

---

## Standoff Geometry

Stepped cylindrical pillars at each mounting hole:

| Section | Z range | OD | ID | Purpose |
|---------|---------|-----|-----|---------|
| Lower shoulder | 2.0 → 4.5 | 5.5 mm | — | PCB-seat shoulder; supports PCB |
| Upper pin | 4.5 → 9.1 | 3.5 mm | — | Passes through PCB hole (Ø4.1 mm); supports plate |
| M2 tap bore | 9.1 → 5.1 (depth 4.0 mm) | — | Ø1.6 mm | M2 self-tapping screw bore, drilled top-down |

---

## Material & Print Notes

- **Filament:** PLA or PETG (PETG preferred for standoff durability)
- **Layer height:** 0.2 mm
- **Wall count:** 4 perimeters minimum (3 mm wall = 7.5 walls at 0.4 mm nozzle)
- **Top/bottom layers:** 5 each
- **Infill:** 25–40% gyroid for floor; full perimeter walls
- **Orientation:** Print bottom-down; no supports needed
- **Standoff M2 tap:** Drive M2 screw into Ø1.6 mm bore to cut threads, or use M2 brass heat-set inserts (requires bore widening to Ø2.7 mm and standoff OD increase to 4.5 mm)

---

## Tests

Run `pytest` after every change. Key test files:
- `test_constants.py` — envelope ≥ PCB+walls, Z stack monotonic
- `test_tray.py` — outer bbox, single solid, MCU hill geometry
- `test_holes.py` — standoff XY matches GERBER T9 positions
- `test_clearances.py` — cutout edges clear component bodies by ≥ 0.3 mm
- `test_manifold.py` — left and right are watertight

---

## Known Risks

- **Encoder knob clearance:** Shaft H20 mm extends well above rim (Z≈26 mm). Knob diameter is user-provided.
- **OLED cover collision:** Separate OLED cover sits between encoder and slide switch. If taller than the wall rim it protrudes above the case.
- **Standoff M2 tap durability:** ~0.95 mm wall around M2 self-tap is marginal. Consider heat-set brass inserts.

---

## OCP CAD Viewer

Every geometry module has an `if __name__ == "__main__":` block that calls `show()`. Run any module directly to preview it:

```bash
source .venv/bin/activate
python src/sofle_case/case.py       # shows case + phantoms (gated by SHOW_*_PHANTOM flags)
python src/sofle_case/tray.py       # shows tray shell
python src/sofle_case/standoffs.py  # shows one standoff
python src/sofle_case/cutouts.py    # shows USB-C cutout
python scripts/build.py left --show # builds + exports + opens viewer
```

**Rule for new files:** any module that produces a `Part` or `Assembly` must include:

```python
if __name__ == "__main__":
    from ocp_vscode import show
    show(<the_part_or_assembly>, name="<descriptive_name>")
```

Keep the import inside the block so `ocp_vscode` remains an optional dev dependency and never breaks production imports.
