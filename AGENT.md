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
├── src/sofle_case/
│   ├── __init__.py
│   ├── constants.py            # all dimensions; SINGLE source of truth
│   ├── pcb_geometry.py         # loads cached PCB polygon JSON
│   ├── tray.py                 # outer shell + cavity + top chamfer
│   ├── standoffs.py            # stepped standoff with M2 tap
│   ├── cutouts.py              # USB-C open-top slot, slide-switch slot
│   └── case.py                 # composes everything; entry point
├── scripts/
│   ├── build.py                # CLI: builds part, exports STL + STEP
│   └── parse_gerber.py         # one-off: extract dimensions from GERBER
├── data/
│   ├── pcb_outline.json        # cached PCB polygon
│   └── mounting_holes.json     # cached mount positions
└── tests/
    ├── test_constants.py       # sanity-check dimensions
    ├── test_dimensions.py      # PCB envelope fits inside cavity
    ├── test_holes.py           # standoff positions match GERBER
    └── test_clearances.py      # cutouts align with components
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
| Slide switch SK12D07VG3 | SW31 | (2.945, −43.23) | **top** | Actuator extends −X past PCB edge |
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
Z =  6.1  ─── PCB top                  (PCB = 1.6 mm)
Z =  7.7  ─── nice!nano PCB top        (MCU_PCB_TOP_Z)
Z =  9.1  ─── switch plate bottom      (PLATE_SEAT_Z)
Z = 10.3  ─── USB-C jack body top      (USB_C_BODY_TOP_Z)
Z = 10.7  ─── switch plate top         (PLATE_TOP_Z, plate = 1.6 mm)
Z = 14.0  ─── main case wall rim       (MAIN_RIM_Z)
Z = 17.1  ─── MCU wall plateau top     (MCU_HILL_Z = PCB_TOP_Z + 11 mm)
```

The −X wall has a variable-height profile above the MCU region: flat plateau at
`MCU_HILL_Z` from the +Y case end to the MCU body −Y edge, then a spline descent
landing at `MAIN_RIM_Z` at the slide-switch Y centre.

---

## Key Constants (from `constants.py`)

### Heights
- `FLOOR_THICKNESS = 2.0`
- `PCB_SEAT_Z = 4.5`
- `PLATE_SEAT_Z = 9.1`
- `MAIN_RIM_Z = 14.0`
- `PCB_TOP_Z = 6.1` (PCB_SEAT_Z + 1.6 mm PCB thickness)
- `PLATE_TOP_Z = 10.7` (PLATE_SEAT_Z + 1.6 mm plate thickness)
- `MCU_PCB_TOP_Z = 7.7` (nice!nano daughter-board top)
- `USB_C_BODY_TOP_Z = 10.3`
- `MCU_HILL_Z = 17.1` (PCB_TOP_Z + 11 mm — −X wall plateau height above MCU)
- `MCU_BODY_L = 33.0` (nice!nano body length in Y, drives plateau extent)
- `PLATE_RAMP_CLEARANCE = 3.0` (mm; MCU wall descent lands ≥ this above PLATE_TOP_Z)

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
- `USB_C_Z_RANGE = (PCB_TOP_Z + 3.0, MAIN_RIM_Z + 0.5)` — open-top slot; bottom 3 mm above PCB top, top punches past wall rim
- `SLIDE_SWITCH_W = 6.0`
- `SLIDE_SWITCH_TOP_W = 14.0`
- `SLIDE_SWITCH_Z_RANGE = (6.1, MAIN_RIM_Z + 0.5)` — punches past wall rim so slot is open to air
- `RESET_PIN_DIA = 2.0`
- `RESET_Z_CENTER = 7.5`

### Component Positions (PCB coords)
- `MCU_POS = (10.27, -16.16)`
- `SW_SLIDE_POS = (2.945, -43.23)`
- `SW_RESET_POS = (7.72, -45.35)`
- `SW_ENCODER_POS = (9.47, -65.95)`
- `J_OLED_POS = (5.22, -33.69)`

### Coordinate Transform
`pcb_to_case(x, y)` translates PCB coordinates to case (outer-rect) coordinates.
- `PCB_OFFSET_X = (OUTER_WIDTH - (PCB_X_MAX - PCB_X_MIN)) / 2 - PCB_X_MIN`
- `PCB_OFFSET_Y = (OUTER_DEPTH - (PCB_Y_MAX - PCB_Y_MIN)) / 2 - PCB_Y_MIN`

---

## Build Sequence (`case.py::build_case_half`)

1. `tray.py::build_tray`:
   a. Build outer shell (PCB polygon offset by WALL_THICKNESS + PCB_XY_CLEARANCE), extrude to MAIN_RIM_Z
   b. Subtract inner cavity (PCB polygon + PCB_XY_CLEARANCE), extruded from FLOOR_THICKNESS upward
   c. Fuse MCU wall cap (−X wall plateau from MAIN_RIM_Z → MCU_HILL_Z above MCU region)
   d. Fillet top rim edges (TOP_CHAMFER = 0.8 mm)
2. Add 5 stepped standoffs at mounting-hole positions
3. Subtract cutouts:
   - USB-C open-top slot in +Y wall (punches past rim)
   - Slide-switch arched-trapezoid slot in −X wall (top-mount, punches past rim)
4. Single STL serves both halves — PCB is reversible. `build_case_half("left")` and `build_case_half("right")` return identical geometry; the parameter only affects export filename.

---

## Cutout Details

### Slide Switch (SK12D07VG3)
- **Wall:** −X outer wall
- **Center:** Y = −43.23 mm (case coords)
- **Shape:** Arched-trapezoid slot — wide at rim (14 mm), narrow at switch level (6 mm), semicircle arch at bottom
- **Z range:** 6.1 → 12.5 mm (PCB top to past wall rim)
- **Depth:** Extrudes from outer face (X=0) past switch body into inner cavity (`PCB_OFFSET_X + SW_SLIDE_POS[0] + 5.0` ≈ 25.7 mm)

**Why top-mount matters:** The switch body sits ON the PCB top surface. The slot must start at `PCB_TOP_Z` (6.1) and extend UP past the wall rim so the actuator is fully exposed to air. If the slot stopped below the rim, a solid wall layer would block finger access.

### USB-C Port
- **Wall:** +Y outer wall
- **Center X:** PCB X = 10.27 mm (case X ≈ 28.02). Both halves share this X — Sofle PCB is reversible, so a single STL serves left and right.
- **Width (X):** 9.0 mm
- **Z range:** 7.5 mm → past rim (open-top slot). Bottom sits just below the nice!nano USB-C jack lower lip (jack body spans Z ≈ 7.9–10.3); top punches past `MAIN_RIM_Z` so cable always has clearance.
- **Y depth:** 31 mm inward from outer wall face. The PCB outline does not extend to the outer wall — ~12 mm of solid case lies between the wall and the cavity edge at MCU X. The slot must reach past the MCU's +Y body edge (case Y ≈ 118.5) into the empty cavity so the cable path is unobstructed.

### Reset Pinhole
- **Wall:** −X outer wall
- **Center:** Y = −45.35 mm
- **Size:** Ø 2.0 mm cylinder along X
- **Z:** 7.5 (button stem mid-height)

---

## Standoff Geometry

Stepped cylindrical pillars at each mounting hole:

| Section | Z range | OD | ID | Purpose |
|---------|---------|-----|-----|---------|
| Lower | 2.0 → 4.5 | 5.5 | — | PCB-support shoulder |
| Upper | 4.5 → 6.5 | 3.5 | — | Passes through PCB Ø4.1 mm hole |
| M2 tap bore | 6.5 → 2.5 (depth 4) | — | 1.6 | Accepts M2 screws from above |

PCB drops over standoffs; switch plate rests on standoff tops at Z=6.5; M2×6 mm screws thread down through plate into standoff bores.

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
- `test_dimensions.py` — PCB fits inside cavity
- `test_holes.py` — standoff XY matches GERBER T9 positions
- `test_clearances.py` — cutout edges clear component bodies by ≥ 0.3 mm

---

## Known Risks

- **Encoder knob clearance:** Shaft H20 mm extends well above rim (Z≈26 mm). Knob diameter is user-provided.
- **OLED cover collision:** Separate OLED cover (TH1, TH2) sits between encoder and slide switch. If taller than the wall rim (12 mm) it protrudes above the case.
- **Standoff M2 tap durability:** 0.95 mm wall around M2 self-tap is marginal. Consider heat-set brass inserts.

---

## OCP CAD Viewer

Every geometry module has an `if __name__ == "__main__":` block that calls `show()`. Run any module directly to preview it:

```bash
source .venv/bin/activate
python src/sofle_case/case.py       # shows the case (single STL, both halves)
python src/sofle_case/tray.py       # shows tray shell
python src/sofle_case/standoffs.py  # shows one standoff
python src/sofle_case/cutouts.py    # shows all cutouts labelled
python scripts/build.py left --show # builds + exports + opens viewer
```

**Rule for new files:** any module that produces a `Part` or `Assembly` must include:

```python
if __name__ == "__main__":
    from ocp_vscode import show
    show(<the_part_or_assembly>, name="<descriptive_name>")
```

Keep the import inside the block so `ocp_vscode` remains an optional dev dependency and never breaks production imports.
