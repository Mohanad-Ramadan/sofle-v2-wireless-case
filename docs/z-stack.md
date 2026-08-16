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
|  26.98 | canopy ridge (roof top) — **right/neutral only** | `canopy_ridge_top_z("right")` |
|  24.22 | canopy ridge (roof top) — **left/flipped only**  | `canopy_ridge_top_z("left")`  |
|  25.48 | USB overmold pocket top (neutral) | `canopy_usb_om_z`       |
|  23.56 | USB-C jack top — **neutral only** | `USB_JACK_NEUTRAL_HI_Z` |
|   21.4 | nice!nano board top (both)        | `MCU_PCB_TOP_Z`         |
|   20.8 | USB-C jack top — **flipped only** | `USB_JACK_FLIPPED_HI_Z` |
|   20.4 | USB-C jack bottom — **neutral only** | `USB_JACK_NEUTRAL_LO_Z` |
|   19.8 | nice!nano board underside (both)  | `MCU_PCB_BOT_Z`         |
|  17.64 | USB-C jack bottom — **flipped only** | `USB_JACK_FLIPPED_LO_Z` |
|   10.4 | main PCB top                      | `PCB_TOP_Z`             |

#### The two MCU orientations

The connector is **mid-mount**: the shell straddles a routed slot in the nano board
rather than sitting on it. It is 3.16 mm tall (`USB_JACK_H`) with a 1.00 mm sink
(`USB_JACK_SINK`), so it hangs 1.00 mm below the board's *component* face and 2.16 mm
(`USB_JACK_PROUD`) above it. The halves are assembled with the nano facing opposite
ways (`C.MCU_ORIENTATION`), which flips which physical face that is:

| half | orientation | jack body | canopy window |
|------|-------------|-----------|---------------|
| left  | flipped (components down) | 17.64 → 20.80 | 16.84 → 21.50 |
| right | neutral (components up)   | 20.40 → 23.56 | 19.60 → 24.26 |

The bands **overlap** through 20.40 → 20.80 and the windows through 19.60 → 21.50.
Query them with `C.usb_jack_z(side)` and `canopy.canopy_usb_z(side)`; never hard-code.

> An earlier revision modelled the shell as 4.0 mm and had the two bands *abut* exactly
> at 20.4. That was a guess, not a measurement — the 4.0 was 1.0 mm of sink plus 3.0 mm
> of assumed protrusion. GCT's Type-C selection guide lists 16-pin mid-mount parts at a
> 3.16 mm profile with 0.80 / 1.00 / 1.60 / 2.10 mm sink options; caliper (≈3 mm shell,
> ≈1 mm buried, ≈2 mm proud) identifies the 1.00 mm sink. Correcting it dropped the ridge
> 26.5 → 25.66.
>
> **`MCU_BOARD_THK` = 1.6 is confirmed** — Mechboards and Keebio both spec the SuperMini at a
> 1.6 mm PCB, the same as the nice!nano v2 it clones. It positions the *flipped* band only;
> the neutral band and the ridge reference the board TOP, which is measured.

#### The port is a STEPPED bore, not a straight hole

The jack mouth sits **3.32 mm behind the canopy's outer face**. A USB-C plug only owns
6.65 mm of shell (`USB_PLUG_SHELL_L`), so a straight shell-sized hole would leave
`6.65 − 3.32 =` **3.33 mm of engagement (50%)** — and its 4.66 mm height would stop the
cable's overmold dead on the outer face anyway. That port would not accept a standard
cable at all.

The receptacle never swallows the whole shell on any device; the case wall hides the rest,
which is why a seated plug *looks* fully inserted. So the bore is stepped:

| section | size | depth |
|---|---|---|
| overmold **pocket** (outer) | 12.85 × 7.00 | 1.67 mm |
| shell **neck** (inner) | 11.00 × 4.66 | 1.08 mm |

> The travel used to read 4.41 mm (2.24 mm / 34% engagement) against a 4.0 mm north wall.
> Both numbers moved at once and for the same reason: the board's north face was anchored to
> the wrong pin (see `MCU_PIN_TO_SOUTH_EDGE`), which put the jack 1.09 mm further south than
> it really sits, and the canopy's north wall was 1.25 mm proud of the tray's own cavity face.
> Fixing the anchor and landing the wall on `BAY_NORTH_INNER_Y` shortened the travel to 3.32
> and the wall to 2.75. The pocket got shallower because the plug now has less wall to cross —
> engagement is unchanged at the 5.0 mm target.

The pocket lets the overmold sink into the wall and the shell picks that depth up
one-for-one, giving `USB_PORT_ENGAGE_TARGET` = **5.0 mm (75%)**. The pocket is sized to the
USB-IF **maximum** overmold (12.35 × 6.50) so any compliant cable fits — overmolds are not
standardised. Both sections are **rounded**, not square: `CANOPY_USB_R` = 1.5 on all four
corners of each (`canopy.usb_port_cutter` builds them as two filleted boxes, so the cutter
carries eight arc faces). The radius is clamped below half the short side, so raising it
degrades a mouth to a stadium rather than failing.

> `USB_PORT_ENGAGE_TARGET` = 5.0 is **not a spec figure** — USB-IF publishes no minimum
> insertion depth. It is anchored on shipping hardware, which runs 0.8–2.0 mm of wall in
> front of the receptacle, i.e. 4.6–5.8 mm of engagement.

#### The ridge is derived PER HALF, not shared

`canopy_ridge_top_z(side)` is the larger of two constraints, both evaluated against THIS
half's own jack/pocket Z:

- the physical stack, `max(usb_jack_z(side)[1], MCU_PCB_TOP_Z) + 0.6 clear + 1.5 roof`.
  On the flipped half the board (21.4) is taller than its OWN jack (20.8), so a jack-only
  derivation would sink the roof into the board — the `max` guards that per half, not just
  on one side.
- the **overmold pocket**, `pocket_top(side) + CANOPY_NORTH_ROUND_R + CANOPY_USB_OM_ROOF_MIN`.

```
right (neutral)  25.66 stack  vs  25.48 + 1.0 + 0.5 = 26.98 pocket  ->  ridge 26.98
left  (flipped)  23.50 stack  vs  22.72 + 1.0 + 0.5 = 24.22 pocket  ->  ridge 24.22
```

Both halves land at the SAME offsets from their own port — `ridge − pocket_top = 1.50` and
`ridge − window_top = 2.72` on both — which is the actual goal: each half carries only as
much roof material as its own port needs, not a shared worst-case. A common ridge (the
previous design) forced the flipped half to sit under the NEUTRAL half's larger offset,
burying its lower port under 2.76 mm of dead air above the roof.

`CANOPY_RIDGE_TOP_Z` still exists as a module constant — `max(canopy_ridge_top_z(s) for s in
("left","right"))`, i.e. always 26.98, the taller half. It survives only because ONE caller
(`case._slide_scoop`) uses it purely as a cut ceiling that removes air above the roof, where
over-reaching on the shorter half is harmless. Every other consumer must call
`canopy_ridge_top_z(side)` directly — the alias is a trap for anything that actually cares
which half it's building.

`CANOPY_NORTH_ROUND_R` dropped 2.5 → 1.0 earlier (part of the stepped-bore work): the north
wall's top round-over eats material from `ridge − R` downward, so a 2.5 mm shoulder would
have forced a taller ridge just to keep the 7 mm pocket buried under it. That trade is
unaffected by going per-half — it just means BOTH halves' ridges are now cheaper than they
would otherwise be, not just the shared one.

The port is cut **twice** — once in `build_canopy`, again in `build_top_part` after the
cover is fused on. That second cut used to be load-bearing: under the old 4.0 mm jack
model the flipped window floor was 15.6, below `COVER_TOP_Z` (16.0), so the cover
backfilled the bottom of the window. The mid-mount correction lifted that floor to 16.84,
clear of the cover — the second cut is now belt-and-braces, kept because it is idempotent
and cheap.

#### The ramp spline used to overshoot its own target curve

The ramp's Y–Z profile is a `Spline` through `CANOPY_RAMP_SAMPLES` points sampled from the
analytic smoothstep, with a forced horizontal tangent at both ends (so it merges into the
cover and the roof with no visible crease). At the historical `CANOPY_RAMP_SAMPLES = 9`, the
interpolated B-spline RANG around that target curve — measured on the fused TOP, up to
**+0.15 mm above and −0.08 mm below** the intended surface, concentrated right where the
ramp flattens into the roof (three sign flips in a ~5 mm span). It was still monotonic, so
the existing smoothness test missed it — monotonicity and flatness are different claims.

`CANOPY_RAMP_SAMPLES` is now **25**. Densifying the interpolation is what damps the ring —
measured on the built west-top ramp edge against the analytic smoothstep:

| samples | right half | left half |
|---|---|---|
| 9 | 0.1426 mm | 0.0865 mm |
| 15 | 0.0731 mm | 0.0400 mm |
| **25** | **0.0318 mm** | **0.0164 mm** |
| 51 | 0.0086 mm | 0.0043 mm |

Roughly 4× less deviation per 2× the samples, and still converging at 51 — an earlier note in
this file claimed a fixed 0.018 mm floor with zero sign flips above 49 samples; re-measurement
supports neither half of that (sign flips persist, 4 of them at 51).

**But deviation is the wrong thing to optimise past this point, and it briefly was.** This was
set to 51 and that detonated the mesh:

| samples | prism triangles | right TOP STL |
|---|---|---|
| 9 | 28,482 | 2.5 MB |
| 15 | 26,988 | — |
| **25** | **39,150** | **3.9 MB** |
| 41 | 216,264 | — |
| 51 | 396,620 | **39.9 MB** |

OCC meshes by **curvature** (angular tolerance), not by deviation. A denser interpolating spline
trades deviation for high-frequency curvature wiggle — the measured max |d²z/dy²| is *worse* at
15–51 (4.5–10.3) than at 9 (1.0), even as the deviation falls. So past ~25 the triangle count
goes up an order of magnitude to buy flatness that is already an order of magnitude below a
0.2 mm layer line. 51 bought 0.023 mm of invisible smoothness for 10× the STL.

The left half never blows up: its ramp is 2.76 mm shorter, so its curvature stays mild
(136k triangles at both 25 and 51). This is a **right-half** failure mode — measure that half.

`test_canopy_ramp_mesh_does_not_detonate` now bounds the canopy's triangle count. Nothing caught
the 51 regression, because every geometric assertion was satisfied: the shape was right and only
the mesh was absurd. 25 is a ceiling, not a target.

#### Densifying the ramp spline silently deleted the west shoulder's facet

Raising `CANOPY_RAMP_SAMPLES` (above) had a side effect nothing caught: it broke
`_round_west_top_edges`. That function chamfered the west wall's top-edge run with a 3-D
`chamfer()`, and OCC rejects a chamfer on the west cap face once the ramp `Spline` is
interpolated through more than ~9 control points. Every fallback failed too — both asymmetric
leg orders, the symmetric leg, and four fillet radii — and the function's last line was
`return part`. So it handed back an unchamfered solid with no error, and the whole west
shoulder went square.

Measured across sample counts, on the selected edge set:

| `CANOPY_RAMP_SAMPLES` | intended `chamfer(2.4, 1.2)` | any fallback | facet volume removed |
|---|---|---|---|
| 9 | works | — | 92.1 mm³ |
| 13, 21 | fails | all fail | **0.0 mm³** |
| 33, 41, 49 | fails | works only at the *shorter* half's ridge | partial |
| 51 (shipped) | fails | all fail | **0.0 mm³** |

The per-half ridge made it worse rather than causing it: at the shorter half's 25.66 ridge some
fallback still rescued the cut, but at the taller half's 26.98 nothing did.

The facet is now cut by `_chamfer_west_top`, a **swept boolean** instead of an edge op. It
ruled-lofts a cutter between two Y–Z sections — one at `x_w − 1` pushed down by the full
vertical leg, one at `x_w + chamfer_h` pushed down by nothing — so ruling linearly in X *is* the
facet plane (drop `chamfer_v` per `chamfer_h` of run). Both sections are built from the body's
own roofline, so the cutter tracks the surface at **any** sample count: verified landing at 9,
13, 21, 51 and 81. Two side benefits: the leg assignment is now explicit (`chamfer_v` vertical,
`chamfer_h` inboard, matching `RIM_FACET_DROP`/`RIM_FACET_RUN` — the old 3-D call left it to OCC,
which applied it the other way round), and the cutter's vertical leg fades to zero at the ramp
foot, where the west wall is only 1 mm tall, so it can never bite into the fuse overlap.

`_chamfer_west_top` **asserts** that it removed material. The silent `return part` is what let
this ship; a no-op there is now a hard failure.

#### The NW corner kink was the missing facet, not the round

`_round_nw_corner` cuts a VERTICAL CYLINDER at the NW corner (west wall ∩ north wall), full
height, to the case's own corner radius. That was briefly replaced by a flat diagonal chamfer,
on the theory that a cylinder is only tangent to VERTICAL walls and so is non-tangent to the
SLOPED north-top chamfer above it — OCC was observed closing the seam with unrelated CONE and
BSPLINE patches, measured up to **64.7°** between adjacent faces: a visible kink, not a blend.

The kink was real but **misattributed**. It was measured on a body whose west top shoulder facet
was silently missing (above), so the cylinder was running into a raw square shoulder instead of
the drafted facet it is designed to meet. With the facet actually cut, the corner resolves to
**exactly one `CYLINDER` face** on both halves — no CONE, no BSPLINE, no kink. The round is
therefore back; the flat mitre was a style regression bought with a misdiagnosis.

`test_canopy_nw_corner_is_rounded` now pins `kinds == ["CYLINDER"]`, so a regression to the
patched-seam state fails loudly instead of being argued about.

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
+11.0 (`MCU_PCB_TOP_Z`), and the mid-mount jack band hangs off whichever board face
the nano's components point at.
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
