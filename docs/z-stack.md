# Z-Stack Reference — Sofle V2 Wireless Case

**Single source of truth for all vertical (Z-axis) geometry.**
All values are defined in `src/sofle_case/constants.py`. Edit there; derived quantities recompute automatically.

---

## Cross-section (side view)

Z=0 is the outer bottom face of the case. All dimensions in mm.

```
Z (mm)

              ┌────────────┐
 20.8 ╌╌╌╌╌╌╌│   S T E M  │╌╌╌╌╌╌╌╌  stem top      Ø 4.5 mm · 3.5 mm tall
              │            │
 17.3 ╌╌╌╌╌╌╌┴────────────┴╌╌╌╌╌╌╌╌  upper housing top
         ╔══════════════════════════╗
         ║                          ║
 17.1 ╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌  MCU hill plateau top (−X / +Y walls at MCU corner)
 14.0 ━━━╬══════════════════════════╬━━━━  case rim top  ← midpoint of upper housing
         ║    U P P E R             ║  15.6 × 15.6 mm
         ║    H O U S I N G         ║  6.6 mm tall
         ║                          ║
 10.7 ╌╌╌╩══════════════════════════╩╌╌╌  plate top · upper housing bottom
      │  ╔══════════════════════════╗  │
      │  ║                          ║  │
      │  ║    S W I T C H           ║  │  1.6 mm FR4
      │  ║    P L A T E             ║  │
      │  ║                          ║  │
  9.1 │  ╚══════════════════════════╝  │  plate seat
      │                                │
      │     ┌──────────────────────┐   │
      │     │   L O W E R          │   │  13.8 × 13.8 mm · 3.0 mm tall
      │     │   H O U S I N G      │   │
      │     │                      │   │
  6.1 │     └──────────────────────┘   │  PCB top · lower housing bottom
      │  ╔══════════════════════════╗  │
      │  ║                          ║  │
      │  ║         P  C  B          ║  │  1.6 mm FR4
      │  ║                          ║  │
  4.5 │  ╚══════════════════════════╝  │  PCB seat
      │                                │
  2.0 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  case floor top
      ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
      ▓▓▓▓▓▓▓▓  solid floor  ▓▓▓▓▓▓▓▓▓  2.0 mm
  0.0 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  case bottom  (Z = 0)
```

---

## Layer table

| Z (mm) | Boundary name         | Thickness | Source                          |
|-------:|-----------------------|----------:|---------------------------------|
|   20.8 | MX stem top           | 3.5 mm    | `switch_phantom._STEM_H`        |
|   17.3 | MX upper housing top  | 6.6 mm    | `switch_phantom._UPPER_H`       |
|   17.1 | MCU hill plateau      | —         | `MCU_HILL_Z`                    |
|   14.0 | Case rim top          | —         | `MAIN_RIM_Z`                    |
|   10.7 | Plate top / MX upper housing bottom | 1.6 mm | `PLATE_TOP_Z`    |
|    9.1 | Plate seat / MX lower housing top   | —      | `PLATE_SEAT_Z`   |
|    6.1 | PCB top / MX lower housing bottom   | 3.0 mm | `PCB_TOP_Z`      |
|    4.5 | PCB seat              | —         | `PCB_SEAT_Z`                    |
|    2.0 | Case floor top        | 2.0 mm    | `FLOOR_THICKNESS`               |
|    0.0 | Case bottom (Z=0)     | —         | *(implicit origin)*             |

Rows above Z=12.0 are **phantom-only** (visual reference; not structural constants).

---

## Per-layer explanations

### Case bottom — Z = 0.0
Z origin of the entire model. The outer bottom face of the printed case shell sits here. All other heights are measured upward from this plane.

### Case floor top — Z = 2.0 (`FLOOR_THICKNESS = 2.0`)
The top surface of the solid floor slab. 2.0 mm is the structural minimum for reliable FDM printing — thin enough to save filament, thick enough to resist bed-separation flex. Standoff lower shoulders start here.

### PCB seat — Z = 4.5 (`PCB_SEAT_Z = 4.5`)
The shoulder surface the main PCB rests on. The gap from the floor top (2.0 mm → 4.5 mm = 2.5 mm) is occupied by the lower section of each stepped standoff. This height was chosen to clear any through-hole solder joints on the PCB underside while keeping the overall case as flat as possible.

### PCB top — Z = 6.1 (`PCB_TOP_Z = 6.1`)
Top surface of the main PCB. Derived from `PCB_SEAT_Z + 1.6 mm` (standard FR4 thickness). The nice!nano daughter board adds another 1.6 mm above this, placing its top at Z = 7.7 (`MCU_PCB_TOP_Z`), and the USB-C jack body reaches Z = 18 (`USB_C_BODY_TOP_Z`) — both used to size the USB-C wall cutout.

### Plate seat — Z = 9.1 (`PLATE_SEAT_Z = 9.1`)
Bottom surface of the switch plate. The 3.0 mm gap above PCB top (6.1 → 9.1) accommodates the lower housing of Cherry MX-style switches. This dimension was **physically measured** on the real hardware stack — it is not a datasheet value. Standoff upper pins span from `PCB_SEAT_Z` (4.5) to `PLATE_SEAT_Z` (9.1), a 4.6 mm span that passes through the 4.1 mm PCB mounting holes and bridges the MX body clearance.

### Plate top — Z = 10.7 (`PLATE_TOP_Z = 10.7`)
Top surface of the switch plate. Derived from `PLATE_SEAT_Z + 1.6 mm` (FR4 switch plate thickness — same material spec as the main PCB). The MX upper housing rests here; switch stems protrude above into the keycap.

### MX switch upper housing — Z = 10.7 → 17.3 (phantom only)
Cherry MX upper body sits directly on the plate top surface. Footprint 15.6 × 15.6 mm, height 6.6 mm. This section protrudes above the case rim — the rim at Z=12.0 shrouds roughly the lower 1.3 mm of the upper housing, leaving ~5.3 mm exposed above the case wall.

### MX switch stem — Z = 17.3 → 20.8 (phantom only)
The stem cylinder (Ø4.5 mm, 3.5 mm tall) rises above the upper housing. Keycaps press-fit onto the stem above this point. The stem top at Z≈20.8 is the highest point in the switch phantom.

### Case rim top — Z = 14.0 (`MAIN_RIM_Z = 14.0`)
Top edge of the case wall. Sits 3.3 mm above the plate top — exactly at the midpoint of the MX upper housing (10.7 → 17.3 mm). The rim bisects the upper housing: the lower half is enclosed by the case wall, the upper half and stem protrude above it for keycap clearance. The USB-C and slide-switch wall openings punch past this rim (top Z = `MAIN_RIM_Z + 0.5` = 14.5) to make them open-top, ensuring one case STL fits both halves regardless of MCU footprint orientation. The −X and +Y walls rise to `MCU_HILL_Z` = 17.1 mm at the MCU corner.

---

## Standoff geometry

Each stepped standoff spans all three seating surfaces:

| Section      | Z range        | Height  | OD     | Purpose                          |
|--------------|---------------|---------|--------|----------------------------------|
| Lower shoulder | 2.0 → 4.5  | 2.5 mm  | 5.5 mm | PCB-seat shoulder; supports PCB  |
| Upper pin    | 4.5 → 9.1    | 4.6 mm  | 3.9 mm | Passes through PCB hole (Ø4.1 mm); supports plate |
| M2 tap bore  | 9.1 → 5.1    | 4.0 mm deep | Ø1.8 mm | M2 self-tapping screw bore, drilled top-down |

---

## Changing a value

Edit the relevant constant in `src/sofle_case/constants.py`. Derived constants (`PCB_THICKNESS`, `PLATE_THICKNESS`, offsets) recompute at import time — no other files need touching.
