# Sofle V2 Wireless — 3D-Printed Tray Case Design

**Date:** 2026-04-25
**Target hardware:** Sofle V2 Wireless PCB (Alt_Switch variant), nice!nano MCU, MX hot-swap switches, EC11 rotary encoder (H20mm shaft), 0.91" OLED, internal LiPo battery.
**Modeling tool:** Build123d (Python, code-CAD).
**Output:** STL + STEP files, one tray per half (left + mirrored right).

---

## 1. Goals & Constraints

Build a printable, reproducible tray-mount case for the Sofle V2 wireless from scratch using parametric Build123d code. The reference STL `SofleRgbBevWifi.stl` (V2 RGB variant) cannot be reused because the wireless V2 differs in:

1. Pinkie column stagger (column 1 has 4 keys not 5; outer columns offset)
2. MCU footprint and orientation (nice!nano with battery sandwiched between MCU and PCB, vs Pro Micro flat)
3. Mounting hole positions (different from RGB variant)
4. PCB outline (irregular polygon with thumb cluster notch and offset top edge)

The case must:
- Hold the PCB on integrated standoffs that go from floor to switch plate
- Provide an open top (no cover above keys)
- Cover the 10mm-tall MCU+header+battery stack for protection
- Expose the rotary encoder, OLED, and switch plate
- Provide cutouts for slide switch (bottom-mount), reset button, and USB-C
- Match MacBook Pro 2021 corner aesthetic (3.5mm radius)

---

## 2. Source Data (extracted, verified)

### 2.1 PCB outline — from `SofleKeyboard-EdgeCuts.gbr`

Bounding box: **143.5 mm wide × 115.5 mm deep**
- X range: −8.5 to 135.0 mm
- Y range: −110.5 to 5.0 mm

The outline is an irregular closed polygon with a stepped top edge (OLED/encoder bumps) and a sloped thumb-cluster cutout in the bottom-left. The full vertex list is parsed at build time from the GERBER file by `pcb_geometry.py`.

### 2.2 Case mounting holes — from `SofleKeyboard-PTH.drl` (T9, Ø4.1mm)

5 positions, all in PCB coordinates:

| # | X (mm) | Y (mm) | Designator |
|---|--------|--------|------------|
| 1 | 14.07 | −80.26 | (TH5 or unmarked) |
| 2 | 39.57 | −19.05 | TH3 |
| 3 | 39.57 | −56.96 | TH6 |
| 4 | 116.07 | −25.66 | TH4 |
| 5 | 116.07 | −63.96 | TH7 |

These are 4.1mm clearance holes — the integrated case standoffs (OD ≤ 3.8mm) pass through with 0.15mm radial clearance.

### 2.3 Component placements — from `CPL-SofleKeyboard.csv`

| Component | Designator | Position (mm) | Rotation | Layer | Notes |
|-----------|-----------|---------------|----------|-------|-------|
| MCU (Pro Micro / nice!nano) | U1 | (10.27, −16.16) | −90° | top | Body ≈ 18×33mm; USB-C exits +Y edge |
| Slide switch SK12D07VG3 | SW31 | (2.945, −43.23) | 270° | **bottom** | Actuator extends −X past PCB edge |
| Reset button (TVBP06) | RSW1 | (7.72, −45.35) | 90° | top | Side-actuated; stem points −X |
| Rotary encoder (EC11 H20) | SW25 | (9.47, −65.95) | 0° | top | 20mm shaft, knob attaches above |
| OLED socket | J3 | (5.22, −33.69) | 90° | top | 5-pin 2.54mm vertical pin socket |
| OLED cover M2 standoffs | TH1, TH2 | (5.40, −52.80), (15.40, −52.78) | — | — | M2 PCB holes for separate OLED cover (NOT case feature) |
| LED | J1 | (33.77, −38.16) | −90° | top | Indicator LED |

**JST battery connector:** S2B-XH-A-1 (2-pin XH, 2.5mm pitch). Wired to internal battery pads. **No case cutout** — battery sits inside case.

### 2.4 Heights — extracted from reference STL `SofleRgbBevWifi.stl`

Major flat-surface Z-values found in the STL (counts of triangles indicate primary horizontal features):

| Z (mm) | Triangles | Feature |
|--------|-----------|---------|
| 0.00 | 139 (down) | Outer floor bottom |
| 2.00 | 165 (up) | Inner floor top — floor thickness = 2mm |
| 4.50 | 240 (up) | PCB seat — PCB rests here |
| 6.50 | 230 (up) | Switch plate seat |
| 10.00 | 360 (up) | Main wall rim top |
| 14.00 | 43 (up) | Reference's tallest feature (RGB build) |

These heights are adopted directly (except the 14mm cap; we extend MCU cover to 17mm — see §3).

---

## 3. Case Geometry

### 3.1 Outer envelope

| Dimension | Value | Source |
|-----------|-------|--------|
| Outer width (X) | 162 mm | PCB 143.5 + 9.25mm border each side |
| Outer depth (Y) | 131 mm | PCB 115.5 + 7.75mm border each side |
| Outer height (main) | 10 mm | Reference STL rim |
| Outer height (MCU cover) | 17 mm | PCB top 6.1 + MCU stack 10 + 0.9mm margin |
| Wall thickness | 3 mm | FDM standard |
| Floor thickness | 2 mm | Reference STL |
| Outer corner radius | 3.5 mm | MacBook Pro 2021 body |
| Top outer chamfer | 1.5 mm × 45° | Reference STL bevel |

### 3.2 Vertical layer stack (bottom → top)

```
Z = 0.0   ─── case bottom (rubber feet stick down ~1mm here)
Z = 2.0   ─── floor interior top
Z = 2.0–4.5  ─── air gap (solder joints, JST connector, battery flat against PCB)
Z = 4.5   ─── PCB bottom (rests on standoff shoulder)
Z = 6.1   ─── PCB top  (PCB = 1.6mm)
Z = 6.5   ─── switch plate bottom (rests on standoff top)
Z = 8.0   ─── switch plate top (plate = 1.5mm)
Z = 10.0  ─── case wall rim
Z = 17.0  ─── MCU cover peak (localized over MCU only)
```

### 3.3 Standoffs — integrated into floor, 5×

Stepped cylindrical pillars at each of the 5 mounting-hole positions (§2.2):

| Section | Z range | OD | ID | Purpose |
|---------|---------|-----|-----|---------|
| Lower | 2.0 → 4.5 mm | 5.5 mm | — | PCB-support shoulder; ring around standoff |
| Upper | 4.5 → 6.5 mm | 3.5 mm | — | Passes through PCB Ø4.1mm hole; supports plate at top face |
| M2 self-tap bore | 6.5 → 2.5 mm (depth 4 mm) | — | 1.6 mm | Threads accept M2 screws from above (through plate) |

- PCB-to-standoff radial clearance: (4.1 − 3.5) / 2 = 0.30 mm — ample for FDM
- Shoulder width: (5.5 − 3.5) / 2 = 1.0 mm — ample PCB seat
- Standoff M2 self-tap wall: (3.5 − 1.6) / 2 = 0.95 mm — adequate in PLA; consider ABS/PETG for durability if reprinted

The PCB drops in over the standoffs; the switch plate rests on the standoff tops at Z=6.5; M2×6mm screws thread down through the plate clearance holes (Ø2.4mm) into the standoff M2 bores, clamping the plate in place. The PCB is captured between the standoff shoulder (Z=4.5) and the plate (Z=6.5) but is not directly screwed.

### 3.4 Inner cavity

The internal cavity (between Z = 2 and Z = 10) follows the PCB outline polygon offset outward by **0.5 mm uniform XY clearance** — NOT a simple rectangle. This preserves the irregular thumb-cluster step and the OLED bump at the top edge, ensuring the PCB seats correctly without rotation.

**PCB support strategy:** The PCB is held only by the 5 stepped standoff shoulders at Z = 4.5 (no perimeter ledge). This simplifies the inner cavity to a single constant offset and avoids manufacturing tolerances on a complex irregular ledge. The standoffs are positioned to give 4-point + 1 anti-flex support.

**Plate support strategy:** The switch plate rests only on the 5 standoff tops at Z = 6.5 (no perimeter ledge). The plate is screwed down with M2 screws into the standoff M2 self-tap bores; the M2 screw heads + plate clearance holes (Ø 2.4 mm) clamp the plate down.

If, after print-test, more support is desired, an optional perimeter ledge can be added at Z = 4.5 by stepping the inner-wall offset from +0.5 mm (above) to +1.5 mm (below) — yielding a 1 mm-wide PCB seat ring all the way around. This is a parameter (`PCB_LEDGE_ENABLED: bool`) in `constants.py`, default `False`.

### 3.5 MCU cover

Localized raised section of the case that **merges with the +Y outer wall** so the MCU cover's +Y face IS the case +Y outer wall in this region (continuous surface, no internal gap for the USB-C connector to traverse).

- Footprint (XY): 23 mm wide × 40 mm deep
- Position: +Y edge **flush with case +Y outer wall** (Y_outer = max_PCB_Y + clearance + wall_thickness ≈ +8.5 mm in PCB coords). Cover therefore extends from Y = +8.5 inward to Y = +8.5 − 40 = −31.5, covering the MCU body (Y range −2.19 to −30.13).
- X centered on MCU: X = 10.27 ± 11.5 mm (covers MCU pin range x=2.42 to 18.12)
- Z range: 10.0 → 17.0 mm (rises 7 mm above main rim)
- Top edge chamfer: 1.5 mm × 45° (matches main case)
- Wall thickness on the raised section: 3 mm (same as main wall)
- Inner cavity: hollow inside, drops to PCB top (Z = 6.1) — encloses MCU + battery + JST connector

The +Y face of the MCU cover, being part of the case +Y outer wall, carries the USB-C cutout (§3.6).

### 3.6 Wall cutouts

| Cutout | Wall | Center (PCB X or Y) | Size | Z range |
|--------|------|---------------------|------|---------|
| USB-C port | +Y outer wall (within MCU-cover raised section) | X = 10.27 mm | 9.0 mm wide × 4.0 mm tall | Z = 12.0 → 16.0 (centered Z=14.0; nice!nano USB-C port is ≈ 8 mm above PCB top) |
| Slide-switch slot | −X outer wall | Y = −43.23 mm | 6.0 mm wide × 3.5 mm tall | Z = 1.0 → 4.5 (matches switch body Z range under PCB) |
| Reset pinhole | −X outer wall | Y = −45.35 mm | Ø 2.0 mm | Z = 7.5 (button stem mid-height: PCB top 6.1 + body half-height ~1.4) |

### 3.7 Floor recess (slide switch body)

The slide switch SW31 is mounted on the PCB BOTTOM. Its body extends 3.5 mm down from PCB bottom. With PCB bottom at Z=4.5, switch body bottom is at Z=1.0 — 1mm BELOW the floor interior top (Z=2.0). A local floor recess is required:

- Footprint: 10 × 5 mm rectangle, centered on (X=2.945, Y=−43.23)
- Depth: 1.5 mm (recess from Z=2.0 down to Z=0.5)
- Floor remaining thickness under recess: 0.5 mm

If 0.5 mm floor proves too fragile in test prints, recess is allowed to break through (open hole in floor). Cover with rubber foot if so.

### 3.8 Bottom feet

Flat rubber adhesive bumpers (user-supplied, 4× per half). Case design provides flat regions for adhesion at the four corners on the case bottom (Z=0) — no integrated geometry required.

---

## 4. Right Half

The data above describes the LEFT half only. The right half is generated as a mirror image about the X=0 plane (i.e., the YZ plane). The build script accepts a `side: Literal["left", "right"]` argument and applies `mirror(part, plane="YZ")` when `side == "right"`. Mounting hole positions, component positions, and cutouts all reflect with the geometry. The two halves are NOT joined — each is a standalone tray.

---

## 5. Build123d Implementation

### 5.1 Project layout

```
sofle_v2_wireless_case/
├── pyproject.toml
├── AGENT.md                    # agent-handoff guide (build+modify workflow)
├── README.md
├── src/sofle_case/
│   ├── __init__.py
│   ├── constants.py            # all dimensions; SINGLE source of truth
│   ├── pcb_geometry.py         # parses GERBER EdgeCuts → ordered polygon Sketch
│   ├── components.py           # CPL-derived component positions
│   ├── tray.py                 # outer shell + cavity + chamfer
│   ├── standoffs.py            # stepped standoff with M2 tap
│   ├── mcu_cover.py            # raised MCU box + USB cutout
│   ├── cutouts.py              # slide switch slot, reset pinhole, floor recess
│   └── case.py                 # composes everything; entry point
├── scripts/
│   ├── build.py                # CLI: builds part, exports STL + STEP
│   └── parse_gerber.py         # one-off: extract dimensions from GERBER → JSON
├── data/
│   ├── pcb_outline.json        # cached PCB polygon (generated)
│   ├── mounting_holes.json     # cached mount positions (generated)
│   └── components.json         # cached CPL positions (generated)
├── output/                     # gitignored; build artifacts
└── tests/
    ├── test_dimensions.py      # PCB envelope fits inside cavity
    ├── test_holes.py           # standoff positions match GERBER
    └── test_clearances.py      # cutouts align with components
```

### 5.2 Single source of truth — `constants.py`

```python
# All dimensions in mm. Change here; everything propagates.

# Heights (Z = 0 at case bottom)
FLOOR_THICKNESS = 2.0
PCB_SEAT_Z      = 4.5
PCB_TOP_Z       = 6.1   # 4.5 + 1.6
PLATE_SEAT_Z    = 6.5
PLATE_TOP_Z     = 8.0   # 6.5 + 1.5
MAIN_RIM_Z      = 10.0
MCU_COVER_Z     = 17.0

PCB_THICKNESS   = 1.6
PLATE_THICKNESS = 1.5

# Outer envelope
OUTER_WIDTH     = 162.0
OUTER_DEPTH     = 131.0
WALL_THICKNESS  = 3.0
CORNER_RADIUS   = 3.5
TOP_CHAMFER     = 1.5

# Standoff geometry
STANDOFF_OD_LOWER = 5.5   # supports PCB
STANDOFF_OD_UPPER = 3.5   # passes through PCB Ø4.1 hole
STANDOFF_TAP_DIA  = 1.6   # M2 self-tap bore
STANDOFF_TAP_DEPTH = 4.0

# Clearances
PCB_XY_CLEARANCE = 0.5
PCB_HOLE_DIA     = 4.1

# MCU cover (merges with +Y outer wall — see §3.5)
MCU_COVER_W = 23.0          # X width
MCU_COVER_D = 40.0          # Y depth (extends inward from +Y wall)

# Cutouts (W = horizontal width along wall, H = vertical height)
USB_C_W, USB_C_H = 9.0, 4.0
USB_C_Z_CENTER   = 14.0     # nice!nano USB-C port mid-height above floor
SLIDE_SWITCH_W, SLIDE_SWITCH_H = 6.0, 3.5
SLIDE_SWITCH_Z_RANGE = (1.0, 4.5)
RESET_PIN_DIA = 2.0
RESET_Z_CENTER = 7.5
SLIDE_SWITCH_RECESS_W = 10.0
SLIDE_SWITCH_RECESS_D = 5.0
SLIDE_SWITCH_RECESS_DEPTH = 1.5

# Component positions (PCB coords, mm)
MCU_POS         = (10.27, -16.16)
SW_SLIDE_POS    = (2.945, -43.23)
SW_RESET_POS    = (7.72,  -45.35)
SW_ENCODER_POS  = (9.47,  -65.95)
J_OLED_POS      = (5.22,  -33.69)

# Mounting holes (PCB coords, mm)
MOUNTING_HOLES = [
    (14.07,  -80.26),
    (39.57,  -19.05),
    (39.57,  -56.96),
    (116.07, -25.66),
    (116.07, -63.96),
]
```

### 5.3 Build sequence (in `case.py::build_case_half`)

```python
def build_case_half(side: Literal["left", "right"]) -> Part:
    pcb_polygon = load_pcb_outline()          # data/pcb_outline.json

    # 1. Outer rounded-rect, extruded to main rim
    outer = (
        Sketch() + RectangleRounded(
            OUTER_WIDTH, OUTER_DEPTH, CORNER_RADIUS
        )
    )
    shell = extrude(outer, MAIN_RIM_Z)

    # 2. Hollow it: subtract inner cavity (PCB outline + 0.5mm) from Z=2 up
    cavity_sketch = offset_polygon(pcb_polygon, PCB_XY_CLEARANCE)
    cavity = extrude(cavity_sketch, amount=MAIN_RIM_Z - FLOOR_THICKNESS,
                     start=FLOOR_THICKNESS)
    shell -= cavity

    # 3. Add internal PCB-seat ledge (perimeter shelf at Z=2 → Z=4.5,
    #    around the irregular cavity edge)
    ledge = build_pcb_ledge(pcb_polygon)
    shell += ledge

    # 4. Add 5 stepped standoffs at mounting-hole positions
    for x, y in MOUNTING_HOLES:
        shell += stepped_standoff(at=(x, y))

    # 5. Add MCU cover box, raises localized region from Z=10 to Z=17
    shell += mcu_cover(at=MCU_POS)

    # 6. Subtract cutouts
    shell -= usb_c_slot(MCU_POS, wall="+Y_inside_mcu_cover")
    shell -= slide_switch_slot(SW_SLIDE_POS, wall="-X")
    shell -= reset_pinhole(SW_RESET_POS, wall="-X")
    shell -= floor_recess_for_slide_switch(SW_SLIDE_POS)

    # 7. Chamfer top outer edges
    shell = chamfer_top(shell, TOP_CHAMFER)

    # 8. Mirror for right half
    if side == "right":
        shell = mirror(shell, plane="YZ")

    return shell
```

### 5.4 GERBER parsing (`pcb_geometry.py`)

Input: `SofleKeyboard-EdgeCuts.gbr`
Output: ordered list of (x, y) tuples forming the closed PCB polygon.

The GERBER EdgeCuts file describes the PCB outline as a series of D02 (move) / D01 (draw) commands at 1e−6 mm precision. The parser:
1. Reads all D02 (start) and D01 (end) coordinates
2. Builds a graph of segments
3. Walks the graph from any starting vertex to produce one ordered loop (the PCB outline is a simple closed polygon)
4. Caches result to `data/pcb_outline.json`

### 5.5 Tests (`tests/`)

- `test_dimensions.py` — sanity-check OUTER_WIDTH > PCB_WIDTH + 2·WALL_THICKNESS, etc.
- `test_holes.py` — verify each standoff XY equals a parsed GERBER T9 hole position (within 0.01mm)
- `test_clearances.py` — verify cutout edges clear component bodies by ≥ 0.3mm
- `test_print_envelope.py` — ensure no part exceeds 250×210mm (typical FDM bed)

---

## 6. Material & Print Notes

- Filament: PLA or PETG. PETG preferred for long-term durability around standoff M2 self-tap.
- Layer height: 0.2mm.
- Wall count: 4 perimeters minimum (case wall is 3mm = 7.5 walls at 0.4mm nozzle).
- Top/bottom layers: 5 each minimum.
- Infill: 25–40% gyroid for the floor; full perimeter walls.
- Orientation: print bottom-down. No supports required if model is correct (vertical walls, integrated standoffs).
- Standoff M2 self-tap: drive an M2 machine screw down into the as-printed Ø1.6mm bore to cut threads on first assembly. Or use M2 brass heat-set inserts (OD 3.0mm) — needs tap bore widened to Ø2.7mm if so.

---

## 7. Out of Scope

- Switch plate (separate part; user provides FR4/PC plate)
- OLED cover (user buys separately; mounts to PCB TH1/TH2)
- Encoder knob (user-provided)
- Wrist rest
- Tenting / tilt feet
- Top bezel or top case
- TRRS jack or any wired-split feature

---

## 8. Acceptance Criteria

A case half is "done" when:
1. `python scripts/build.py left` and `python scripts/build.py right` both produce STL + STEP without errors
2. All `pytest` tests pass
3. Imported into a slicer, the model has no manifold errors
4. Visually inspected in MeshLab / FreeCAD: PCB outline matches the inner cavity within 0.5–0.8mm clearance everywhere; all 5 standoffs visible; MCU cover box visible at top-left; USB-C, slide switch, and reset cutouts visible
5. PCB physically fits over standoffs in the printed case with light pressure (no hammering, no rattle); switch plate rests flat on standoff tops; switches retain plate.

---

## 9. Open Questions / Risks

- **Encoder knob clearance**: Encoder shaft H20mm extends well above rim (Z≈26mm). Knob diameter is user-provided; case has no constraint here.
- **OLED cover collision**: Separate OLED cover (TH1, TH2) sits between encoder and slide switch. If cover is taller than 17mm, it would protrude above the MCU cover. User must confirm cover height when sourcing.
- **Floor recess fragility**: 0.5mm floor remaining under slide-switch recess may crack. Fallback: open hole, hidden by rubber foot.
- **Standoff M2 tap durability**: 0.95mm wall around M2 self-tap is marginal. Consider heat-set brass inserts (M2 OD 3.0mm) — requires increased standoff OD to 4.5mm and corresponding tap bore widening.
