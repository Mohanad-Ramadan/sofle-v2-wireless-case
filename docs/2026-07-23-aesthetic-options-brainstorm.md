# Making the case look better — brainstorm options

The case reads as a tall, flat-sided slab (16 mm wall = `COVER_TOP_Z`, ~28 mm with keycaps),
ugly from the sides. These are the options brainstormed to fix that, all sized against the real
geometry.

## Hard constraints that shape every option
- **Front (south / −Y) face:** a flat vertical slab, Z 0 → 16.0 (`COVER_TOP_Z`).
- **Wall thickness** = 4.75 (`WALL_THICKNESS`).
- **Rabbet-skin limit:** below `SEAM_LEDGE_Z = 6.3` the tub's outer skin is only `SEAM_SKIN = 2.0`
  thick (rabbet pocket behind it), so **exterior sculpting below Z = 6.3 can bite ≤ ~0.5 mm**.
  Above 6.3 you can bite up to ~3.25 mm and still keep ≥1.5 mm wall.
- **OCC quirk:** it rejects an *asymmetric* `chamfer()` on this arc-offset rim edge set, so any
  big facet must be built as **loft / wedge cutter solids**, not `chamfer()`.
- Good news: `tray.offset_extruded()` already lofts between two polygon offsets, so a facet can
  follow the irregular Sofle outline (incl. thumb cluster) for free.

---

## Option 1 — Aggressive south facet (the core idea) ⭐
A steep planar bevel eating the top of the front wall so it reads about **half height**, like
premium alloy boards do on the hands' inner face.
- Budget: horizontal run ≤ 3.25, vertical drop down to the ledge ≤ ~9.7.
- Proposal: `FRONT_FACET_DROP = 8.0`, `FRONT_FACET_RUN = 3.0` → ~69° facet, Z 16 → 8. Remaining
  vertical face ~1.7 mm + bottom chamfer → front reads half-height, catches light like machined alu.
- 45° won't do it here (45° caps at ~3.25 drop). A **steep** facet is the move; ~30°-from-vertical
  also matches the forearm approach angle ergonomically.
- Two variants:
  - **South-only** (mask to the front) — emphasized front, needs end-blending where it dies into
    the side treatment.
  - **Full-perimeter drafted rim** — the whole top becomes a sloped roofline, then deepen only the
    south side. Simpler geometry, reads as one sculpted object.
- Print: the tub prints top-face-down → the facet becomes a ~21° overhang. No supports.

## Option 2 — Shadow-line reveal groove
A classic ID trick. A **0.8 wide × 0.6 deep V-groove** around the perimeter at **Z ≈ 6.8** (just
above the ledge, in full-thickness wall) visually splits the 16 mm slab into ~9.2 + 6.8, faking a
premium two-piece case. V-profile is self-supporting in any print orientation. ~20 lines of code.

## Option 3 — Two-tone filament swap at the groove
The tub prints flat → layer bands are horizontal → swap filament color at the print-Z that matches
the groove line. The groove masks the transition seam. Zero extra geometry beyond Option 2.
Biggest looks-per-effort win — the slab stops reading as one tall block entirely.

## Option 4 — Upgrade the remaining top edge
Where the facet doesn't run (or on top of it): grow the old 1.9 mm chamfer → 3.0, or go **hybrid
fillet-over-chamfer** — a ≥40° chamfer at the base rising into a fillet — reads as a full round-over
from desk level but stays FDM support-free.

## Option 5 — Floating-plinth undercut at the ground
A **0.5 bite × 2–3 mm tall** near-vertical draft around the base → a thin shadow gap so the case
appears to "float." Capped at 0.5 mm depth by the rabbet skin, but shadow lines don't need depth to
read.

## Option 6 — E/W side scoops
The "tall from the sides" complaint is the east/west elevation. A long shallow **concave cove**
(1.0–1.5 deep, cylinder-swept) mid-height along the E/W walls breaks up the slab and doubles as a
lift grip. Keep it above Z = 6.3.

## Option 7 — Actually shrink it *(user ruled this out)*
Solder the 12 battery-overlap switches (−2.0), `BATTERY_FLOOR_BASE` 2.0 → 1.2 (−0.8), cover 1.0 →
0.8 (−0.2) → wall 16 → ~13 mm. Combined with Option 1 the front face nearly vanishes.

## Option 8 — Rear tilt feet
3–5° wedge feet at the rear `FOOT_POSITIONS` → adds typing angle and drops the front from the user's
POV. Pairs with (doesn't replace) the facet. **Trap:** the rear feet sit at different Y (110 vs 104),
so each riser needs its own height derived from `FOOT_POSITIONS` + the angle, and all four contact
points cut by one shared tilted plane so the case doesn't rock.

---

## Recommended combo (from the brainstorm)
**Option 1 (full-perimeter drafted rim, south deepened) + 2 + 3**, optionally 7 later — the three
tricks premium cases actually stack: a sculpted sloped rim, a shadow-line split, and a two-tone
band. All FDM-safe, all above the rabbet constraint, all parametric via `offset_extruded` lofts +
new `FRONT_FACET_*` constants.

## What the user chose
**1 + 2 + 3 + 8** (7 was ruled out), each verified one at a time.

## Status note (as of 2026-08-01)

| Option | State |
|---|---|
| **1** — drafted rim facet + aggressive south facet | **done, committed** (`47f8033`…`c5462f5`) |
| **2** — shadow-line reveal groove | built + green, then **PARKED** — see *Parked work* below |
| **3** — two-tone filament swap | **blocked** — it keys off the groove line, which is parked |
| **8** — rear tilt feet | built + green, then **PARKED** — user will pick it up when needed |
| 4, 5, 6 | not chosen |
| 7 — shrink the case | ruled out by the user |

**Net effect on the case so far: Option 1 only.** 2 and 8 were each built and verified, then set
aside — 2 because it was not wanted, 8 because it is a later job. The shipped geometry is the
drafted rim facet and nothing else from this list.

## Parked work — how to get it back

Both parked options live in `git stash`, complete with their tests. **Do not trust the indices
below** — every new stash pushes them down. Run `git stash list`, find the entry by its message,
then use the index you actually see:

```
git stash list                        # look for "Option 2: …" / "Option 8: …"
git stash show -p 'stash@{N}'         # review before applying
git stash apply 'stash@{N}'           # bring it back (docs will conflict — keep the tree's)
```

Each stash is a full snapshot of the tree at the time it was parked, so it also carries the
docs as they read then. Take the working tree's version of any doc conflict.

---

**Option 1** took several rounds. The sticking point was the SW: the deep facet's boundary throws a
crease, and the thumb wall is bounded by plan corners at both ends, so every attempt to *tune* the
mask produced two creases instead of one. It was solved by not tuning the West at all — the West
`/` is now **derived** as an exact mirror twin of the East `\` (same X-run and angle, centred on
the thumb-switch midpoint), so the pair reads as symmetric in front elevation even though the
outline underneath is asymmetric. Two later fixes finished it: closing the facet handover gap at
the +Y bump, and rebuilding the facet as a drafted prism rather than a loft (an outward arc-offset
doesn't preserve edge count, so the loft was being approximated by skewed splines — that was the
real source of the wandering creases).

**Option 2 — parked, not wanted.** Worth knowing if it is ever revived: the groove is squeezed into
a **1.4 mm window** between the rabbet-pocket ceiling at Z=6.6 (below it the outer skin is only
2.0 mm — the skirt the plate slides into) and the south facet toe at Z=8.0. It therefore came out
0.7 tall × 0.5 deep at Z 6.9–7.6, not the 0.8 × 0.6 this brainstorm assumed, leaving a 0.4 mm land
under the facet toe. On the palm-facing wall it reads as a line tucked under the bevel rather than
a clean split; the split only really reads on the E/W and back elevations. The +Y relief bump needs
its own face-aligned cutters because it stands proud of the nominal outline offset — the same
problem, and the same fix, as the facet.

**Option 3 is blocked** while 2 is parked: the filament swap has no line to hide its colour
transition in. Doing it anyway would put a visible seam mid-wall.

**Option 8 — parked for later.** It was built as `src/sofle_case/feet.py`: two optional pucks per
half dropping into the existing rear rubber-foot seats, 4.000° of pitch, no case changes at all.
Three things it learned that are worth not rediscovering:

- The differing rear foot Y (110 vs 104) is **not** the hard part. Give each X column its own lift
  `tan(tilt) × (y_rear − y_front)` and the four ground contacts come out *exactly* coplanar — the
  triple product cancels algebraically for any foot layout, so the case cannot rock at any angle.
- Each riser's body must be `lift − FOOT_DEPTH` tall, not `lift`: the FRONT pads sit recessed
  0.6 mm in their seats while the rear pads sit flat under the risers.
- **The real trap is the case nose, which this brainstorm missed entirely.** 22 mm of case hangs in
  front of the front feet (seats at y=22/38, thumb corner at y≈0.5), and it drops 1.50 mm at 4°. So
  the stick-on pads must be **at least 3.0 mm thick** or the front corner grounds before the feet
  do — 2.0 mm pads fail by 0.1 mm. Any future tilt scheme has to clear this, whatever form it takes.

There is also an inherent **0.52° side lean** on top of the 4° pitch, because the FRONT seats sit at
different Y too, making the pivot line oblique in plan. Removing it would take a third riser under
the front-west seat.

See `docs/2026-07-23-handoff-aesthetic-refinements.md` for the running detail and
`.omc/plans/2026-07-23-case-aesthetic-refinements.md` for the 4-phase plan.

## Sources consulted
- BigRep — fillets vs chamfers in 3D printing
- WeFab / Geeetech — chamfer vs fillet edge treatments
- Bambu forum — hybrid chamfer-fillet technique
- Eureka Ergonomic — beveled edges & wrist health (front-bevel angle)
- attackshark — wrist-rest selection vs case front height & inclination
- kbd.news — keyboard case design (reference)
