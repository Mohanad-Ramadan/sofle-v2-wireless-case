# Z-Stack Reference — Sofle V2 Wireless Case

**Single source of truth for all vertical (Z-axis) geometry.**
All values are defined in `src/sofle_case/constants.py`. Edit there; derived quantities recompute automatically.

This is the **minimal short case**: the perimeter walls end flush with the switch
plate's top surface (`MAIN_RIM_Z == PLATE_TOP_Z`). There is no MCU hill — every
perimeter wall is flat at the rim. The MCU bay is hooded by the fastback canopy,
which is fused into the TOP part.

> ⚠️ **Partially stale.** Everything outside the *MCU stack* section below predates
> the `FLOOR_THICKNESS` 3.8 → 6.3 change, so its absolute Z values read 2.5 mm low
> (`PCB_TOP_Z` is shown as 7.9; it is 10.4). The MCU stack section is current and
> caliper-measured. Trust `constants.py` over this file until the rest is regenerated.

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

**Caliper-measured** on the real hardware, referenced to the main PCB top face
(`PCB_TOP_Z` = 10.4). Unlike the rest of this document, these values are current.

The bay is no longer open air: the fastback canopy (`canopy.py`) is fused into the
TOP and hoods the whole MCU, with the USB-C port punched through its north wall.

| Z (mm) | Boundary                          | Source                  |
|-------:|-----------------------------------|-------------------------|
|   26.5 | canopy ridge (roof top)           | `CANOPY_RIDGE_TOP_Z`    |
|   25.0 | canopy roof underside             | ridge − `CANOPY_ROOF_WALL` |
|   24.4 | USB-C jack top — **neutral only** | `USB_JACK_NEUTRAL_HI_Z` |
|   21.4 | nice!nano board top (both)        | `MCU_PCB_TOP_Z`         |
|   20.4 | jack seam: neutral bottom = flipped top | `USB_JACK_*`      |
|   16.4 | USB-C jack bottom — **flipped only** | `USB_JACK_FLIPPED_LO_Z` |
|   10.4 | main PCB top                      | `PCB_TOP_Z`             |

#### The two MCU orientations

The halves are assembled with the nice!nano facing opposite ways
(`C.MCU_ORIENTATION`), so the same 4.0 mm connector lands at two different heights:

| half | orientation | jack body | canopy window |
|------|-------------|-----------|---------------|
| left  | flipped (components down) | 16.4 → 20.4 | 15.6 → 21.1 |
| right | neutral (components up)   | 20.4 → 24.4 | 19.6 → 25.1 |

The bands abut at 20.4 — the nano board's underside — and the windows overlap
through 19.6 → 21.1. Query them with `C.usb_jack_z(side)` and
`canopy.canopy_usb_z(side)`; never hard-code.

The **ridge is common to both halves** at 26.5, derived from
`max(USB_JACK_NEUTRAL_HI_Z, MCU_PCB_TOP_Z) + 0.6 clear + 1.5 roof wall`. The `max`
matters: on the flipped half the board (21.4) is taller than its jack (20.4), so a
jack-only derivation would sink the roof 0.4 mm into the board. The left half could
safely drop to 23.5, but a common ridge was chosen so the halves keep an identical
silhouette.

The flipped half's window floor (15.6) dips below `COVER_TOP_Z` (16.0), so the port
is cut **twice** — once in `build_canopy`, again in `build_top_part` after the cover
is fused on. Without the second cut the cover backfills the bottom of the window.

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
thickness). It is also the reference face for every measured MCU height — see the
*MCU stack* section above, which supersedes this paragraph: the nano board top is
+11.0 (`MCU_PCB_TOP_Z`), and the jack band depends on which way the nano faces.
The port is **not** open over the rim; it is cut through the canopy's north wall.

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
