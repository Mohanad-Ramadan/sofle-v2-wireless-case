# Z-Stack Reference — Sofle V2 Wireless Case

**Single source of truth for all vertical (Z-axis) geometry.**
All values are defined in `src/sofle_case/constants.py`. Edit there; derived quantities recompute automatically.

This is the **minimal short case**: the perimeter walls end flush with the switch
plate's top surface (`MAIN_RIM_Z == PLATE_TOP_Z`). There is no MCU hill — every
wall is flat at the rim, and the nice!nano + USB-C jack sit open above it.

---

## Cross-section (side view, switch column)

Z=0 is the outer bottom face of the case. All dimensions in mm.

```
Z (mm)
                  ┌────────────┐
 22.6 ╌╌╌╌╌╌╌╌╌╌╌│   S T E M  │╌╌╌╌╌╌╌╌  stem top          Ø4.5 mm · 3.5 mm tall
                  │            │
 19.1 ╌╌╌╌╌╌╌╌╌┬─┴────────────┴─┬╌╌╌╌╌╌  upper housing top
               │                │
               │  U P P E R     │   15.6 × 15.6 mm
               │  H O U S I N G │   6.6 mm tall  (fully above the rim)
               │                │
 12.5 ━━━┓─────┴────────────────┴─────┏━━  case rim top = plate top  (walls flush)
         ┃  ╔══════════════════════╗  ┃
         ┃  ║   S W I T C H  P L.   ║  ┃   1.6 mm FR4 switch plate
 10.9 ───┃──╚══════════════════════╝──┃──  plate seat · MX lower housing top
         ┃     ┌──────────────────┐   ┃
         ┃     │  L O W E R        │   ┃   13.8 × 13.8 mm · 3.0 mm tall
         ┃     │  H O U S I N G    │   ┃   (measured MX body clearance gap)
  7.9 ───┃─────└──────────────────┘───┃──  PCB top · MX lower housing bottom
         ┃  ╔══════════════════════╗  ┃
         ┃  ║        P  C  B        ║  ┃   1.6 mm FR4
  6.3 ───┃──╚══════════════════════╝──┃──  PCB seat
         ┃                            ┃
  3.8 ━━━┛━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┗━━  case floor top
         ▓▓▓▓▓▓▓▓░░░░ battery ░░░░▓▓▓▓▓▓
  2.0 ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  battery-pocket floor (2.0 mm solid below)
      ▓▓▓▓▓▓▓▓▓▓▓▓▓ solid floor ▓▓▓▓▓▓▓▓▓
  0.0 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  case bottom  (Z = 0)
```

The upper housing and stem (Z 12.5 → 22.6) protrude entirely above the case wall
— nothing shrouds them, since the rim is flush with the plate top.

---

## Layer table

| Z (mm) | Boundary name                        | Thickness | Source                    |
|-------:|--------------------------------------|----------:|---------------------------|
|   22.6 | MX stem top                          | 3.5 mm    | `switch_phantom._STEM_H`  |
|   19.1 | MX upper housing top                 | 6.6 mm    | `switch_phantom._UPPER_H` |
|   12.5 | **Case rim top = plate top**         | 1.6 mm    | `MAIN_RIM_Z` / `PLATE_TOP_Z` |
|   10.9 | Plate seat / MX lower housing top    | 3.0 mm    | `PLATE_SEAT_Z`            |
|    7.9 | PCB top / MX lower housing bottom    | 1.6 mm    | `PCB_TOP_Z`               |
|    6.3 | PCB seat                             | —         | `PCB_SEAT_Z`              |
|    3.8 | Case floor top                       | 1.8 mm    | `FLOOR_THICKNESS`         |
|    2.0 | Battery-pocket floor                 | 2.0 mm    | `FLOOR_THICKNESS − BATTERY_POCKET_DEPTH` |
|    0.0 | Case bottom (Z=0)                    | —         | *(implicit origin)*       |

Rows above the rim (Z > 12.5) are **phantom-only** — visual reference for the MX
switch, not structural case geometry.

### MCU stack (at the MCU corner, not the switch column)

The nice!nano and its USB-C jack sit above the flat +Y / −X walls at the MCU
corner. These heights drive the PCB phantom's MCU/jack visuals only — there is no
case material above the rim there:

| Z (mm) | Boundary                     | Source             |
|-------:|------------------------------|--------------------|
|   19.8 | USB-C jack body top          | `USB_C_BODY_TOP_Z` |
|   18.9 | MCU + header legs top        | `MCU_HILL_Z`       |
|   13.8 | nice!nano PCB top            | `MCU_PCB_TOP_Z`    |

---

## Per-layer explanations

### Case bottom — Z = 0.0
Z origin of the entire model. The outer bottom face of the printed case shell sits
here. All other heights are measured upward from this plane.

### Battery-pocket floor — Z = 2.0
A 405070 LiPo cell recesses `BATTERY_POCKET_DEPTH` (1.8 mm) into the underside of
the floor, leaving 2.0 mm of solid material beneath it — the same effective floor
thickness the case has everywhere else.

### Case floor top — Z = 3.8 (`FLOOR_THICKNESS = 3.8`)
Top surface of the solid floor slab. It is 1.8 mm thicker than the structural
minimum (2.0 mm) precisely so the battery pocket can be sunk into it without
thinning the load-bearing floor. Standoff lower shoulders start here.

### PCB seat — Z = 6.3 (`PCB_SEAT_Z = 6.3`)
The shoulder surface the main PCB rests on. The 2.5 mm gap above the floor top is
occupied by the lower section of each stepped standoff and clears any through-hole
solder joints on the PCB underside.

### PCB top — Z = 7.9 (`PCB_TOP_Z = 7.9`)
Top surface of the main PCB. Derived from `PCB_SEAT_Z + 1.6 mm` (standard FR4
thickness). The nice!nano daughter board adds ~5.9 mm above this (`MCU_PCB_TOP_Z`
= 13.8), and its USB-C jack body reaches Z ≈ 19.8 (`USB_C_BODY_TOP_Z`) — both
above the flat wall, so the port is accessible over the rim with no cutout.

### Plate seat — Z = 10.9 (`PLATE_SEAT_Z = 10.9`)
Bottom surface of the switch plate. The 3.0 mm gap above PCB top accommodates the
lower housing of Cherry MX-style switches. This was **physically measured** on the
real hardware stack, not taken from a datasheet. Standoff upper pins span
`PCB_SEAT_Z` (6.3) → `PLATE_SEAT_Z` (10.9), passing through the Ø4.1 mm PCB holes
and bridging the MX body clearance.

### Plate top / case rim — Z = 12.5 (`PLATE_TOP_Z == MAIN_RIM_Z`)
Top surface of the switch plate, derived from `PLATE_SEAT_Z + 1.6 mm`. The case
wall ends at exactly this height: the rim is left **sharp** (no bevel) so the wall
top reads as one continuous flush surface with the plate. Every wall is flat here
— the slide-switch access valley on the −X wall dips below it, and the +Y B+/B-
relief bump widens the wall outward at the MCU column, but nothing rises above it.

### MX switch upper housing — Z = 12.5 → 19.1 (phantom only)
Cherry MX upper body sits directly on the plate top. Footprint 15.6 × 15.6 mm,
6.6 mm tall — fully exposed above the case wall.

### MX switch stem — Z = 19.1 → 22.6 (phantom only)
The stem cylinder (Ø4.5 mm, 3.5 mm tall) rises above the upper housing; keycaps
press-fit onto it. Z ≈ 22.6 is the highest point in the switch phantom.

---

## Standoff geometry

Each stepped standoff spans the floor-to-plate seating surfaces:

| Section        | Z range      | Height      | OD      | Purpose                                   |
|----------------|--------------|-------------|---------|-------------------------------------------|
| Lower shoulder | 3.8 → 6.3    | 2.5 mm      | 5.5 mm  | PCB-seat shoulder; supports PCB            |
| Upper pin      | 6.3 → 10.9   | 4.6 mm      | 3.9 mm  | Passes through PCB hole (Ø4.1 mm); supports plate |
| M2 tap bore    | 10.9 → 6.9   | 4.0 mm deep | Ø1.8 mm | M2 self-tapping screw bore, drilled top-down |

---

## Changing a value

Edit the relevant constant in `src/sofle_case/constants.py`. Derived constants
(`PCB_THICKNESS`, `PLATE_THICKNESS`, offsets) recompute at import time — no other
files need touching. Re-run `pytest` afterward; `test_constants.py` guards the
Z-stack ordering and the derived-thickness identities.
