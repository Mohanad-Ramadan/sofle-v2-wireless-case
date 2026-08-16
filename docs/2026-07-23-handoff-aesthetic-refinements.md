# Handoff — Case Aesthetic Refinements

**Started:** 2026-07-23 · **Last updated:** 2026-08-01
**Branch:** `feat/sandwich-minimal-case`
**Options doc:** `docs/2026-07-23-aesthetic-options-brainstorm.md` (the 8 options and why)
**Full plan:** `.omc/plans/2026-07-23-case-aesthetic-refinements.md` (4 phases)

| Phase | What | Status |
|---|---|---|
| 1 | Drafted rim facet + aggressive south facet | **DONE, committed** (`47f8033`…`c5462f5`) |
| 2 | Shadow-line reveal groove | built + green, then **PARKED** at the user's request — in `git stash` |
| 3 | Two-tone filament-swap doc | **blocked** — keys off the groove line, which is parked |
| 4 | Rear tilt riser feet | built + green, then **PARKED** for later — in `git stash` |

---

## 0. Environment / commands

- Python venv: **`.venv/bin/python`** (build123d 0.10.0). System `python`/`python3` do NOT have build123d.
- Tests: `.venv/bin/python -m pytest -q` — **142 passing**, ~130 s.
- Build/export a half: `.venv/bin/python scripts/build.py right` (and `left`) → writes
  `output/sofle_{right,left}_{top,bottom}.{stl,step}`. The shipped design is the **sandwich**
  (TOP tub + BOTTOM plate); `build_case_half` is a legacy single-piece tray behind `--legacy`.
- **Interactive viewer:** `.venv/bin/python -m sofle_case.case` — as a MODULE, not
  `python src/sofle_case/case.py` (relative imports make the file-path form fail). Shows both
  parts and the phantoms. `scripts/build.py <side> --show` shows the same thing plus whatever it
  just exported.
- **Offline renders (no interactive OCP viewer needed)** — `scripts/dev/`:
  - `render.py <stl> <out.png>` — 3 whole-part views.
  - `section.py <stl> <out.png>` — Y-Z cross-sections at X=40 and X=80.
  - `render_corner.py <stl> <out.png> <xlo> <xhi> <ylo> <yhi> "title"` — zoomed, clean
    (full-triangle clip). SW corner crop: `0 50 -3 42`; SE corner crop: `95 155 10 60`.
- **Point probes on arc-offset walls are UNRELIABLE** for judging *shape* (the exact wall X/Y is
  hard to hand-compute through a Kind.ARC offset). Probes are fine for "is there material here";
  use renders and cross-sections to judge how something looks.

---

## 1. Fixed geometry facts (verified against `constants.py`, 2026-08-01)

| Fact | Value | Note |
|---|---|---|
| Tub rim (sandwich TOP) | `COVER_TOP_Z = 16.0` | `MAIN_RIM_Z 15.0 + COVER_THICKNESS 1.0` |
| Legacy tray rim | `MAIN_RIM_Z = 15.0` | `build_tray()` default |
| Wall thickness | `WALL_THICKNESS = 4.75` | envelope derives from it |
| Floor / rabbet ledge | `FLOOR_THICKNESS = SEAM_LEDGE_Z = 6.3` | the split height |
| Rabbet-pocket ceiling | `SEAM_LEDGE_Z + SEAM_LEDGE_CLEAR = 6.6` | anything exterior must clear this |
| Outer skin below the ledge | `SEAM_SKIN = 2.0` | **exterior bites below Z=6.6 must be ≤0.5 mm** |
| Membrane fuse band | inner `COVER_FUSE_MARGIN = 1.0` of wall | facet must not reach it |
| Outer perimeter length | ≈ 508 mm | used by the groove continuity test |
| OCC rejects asymmetric `chamfer()` on the rim edge set | — | facets MUST be cutter solids |

> The inline "13.5" / "3.8" / "12.5" comments that used to contradict these were stale literals
> from before `FLOOR_THICKNESS` went 3.8 → 6.3; they were corrected on 2026-08-01. Values above
> are the live ones.

The TOP is a deep tub owning the full outer skin to the ground (no outer seam). `build_tray(rim_z)`
builds outer shell + cavity + MCU +Y relief bump + rim facets + shadow groove, and is called by both
`build_case_half` (rim 15) and `build_top_part` (rim 16, which then adds membrane/encoder/canopy and
cuts the plate pocket and slide scoop).

### South (palm-facing) outline, case coords (inner polygon; outer wall = +5.25 offset, Kind.ARC)
- **E0** (5.2, 30.2) → (19.8, 5.2)   — SW **thumb wall**
- **E1** (19.8, 5.2) → (36.8, 15.2)  — ramp1
- **E2** (36.8, 15.2) → (54.2, 23.2) — ramp2
- **E3** (54.2, 23.2) → (110.8, 23.2)— central front (the long 56 mm span)
- **E4** (110.8, 23.2) → (148.8, 33.2)— SE ramp
- West wall starts at case-y ≈ 24.75; E/W walls face ±X.

---

## 2. Phase 1 — drafted rim facet (DONE)

Goal: the 16 mm flat wall read as an ugly tall slab. It is replaced by a **drafted facet** all round
(shallow) plus a **deeper facet on the palm-facing south run** so the front reads about half height.
Prints support-free (the tub prints top-face-down → the facets become 20–27° overhangs).

Constants (`constants.py`): `RIM_FACET_DROP 4.0` / `RIM_FACET_RUN 2.0` (perimeter),
`FRONT_FACET_DROP 8.0` / `FRONT_FACET_RUN 3.0` (south), `FRONT_FACET_Y_MASK 24.0`,
`REFLEX_ROUND_R 2.0`, plus 4 import-time asserts. `OUTER_TOP_CHAMFER = 1.9` stays defined
(canopy.py reads it as a wall-inset offset) but is no longer applied to the rim.

Key implementation points in `tray.py` — all of these were hard-won, do not undo them casually:

- **Drafted prism, not a loft** (`_rim_facet_frustum`, commit `c5462f5`). Lofting between two
  Kind.ARC offsets of the same wire fails because an outward arc-offset does NOT preserve edge
  count (23 vs 24 edges at the perimeter amounts, 23 vs 27 at the front ones). With no 1:1 vertex
  correspondence OCC gives up on ruled surfaces and approximates the band with skewed BSpline
  patches — that was the original source of the wandering creases and the dipping toe line.
  `LocOpe_DPrism` drafts each face in place, so a straight outline segment yields an exact PLANE
  and an arc corner an exact CONE. `test_facet_is_exact_planes_and_cones` guards this.
- **Reflex corners rounded in the 2-D profile** (`_rounded_wire` / `REFLEX_ROUND_R`). A Kind.ARC
  offset rounds convex corners but leaves reflex ones as sharp V-notches, each throwing a spurious
  crease. Rounding them in the profile means wall AND facet flow through by construction. The
  CAVITY keeps the sharp polygon, so PCB fit is unchanged.
- **The +Y bump gets its own face-aligned wedges** (`_mcu_bump_exclusion` + `_bump_face_facets`).
  The bump is proud of the nominal outline offset, so the polygon cutter would tunnel grooves
  *inside* it. Both sides read `_bump_facet_south_y()` so the handover cannot drift — they once
  disagreed by 0.15 mm and left a 4 mm razor fin at the rim.

### The SW crease problem — RESOLVED (this is what the old handoff called "unresolved")
The deep→shallow boundary of the south facet shows as a crease. The user wanted the SW to read as
**one** crease, mirroring the SE one that "looks good by accident". Attempts that just moved the
mask boundary kept producing two creases, because the thumb wall E0 is bounded by plan corners at
BOTH ends. The fix that landed (`aac4dde`, `8dc15b3`) was to stop tuning the West at all:

- **East `\`** = the flat cap `y = FRONT_FACET_Y_MASK` crossing the rising SE ramp E4. Unchanged.
- **West `/`** = **derived**, not tuned: the East crease's X-run mirrored (rim east of toe) and
  centred on `pcb_geometry.thumb_switch_midpoint_x()`, dropped onto the SW thumb ramp. Same
  run and angle as the East by construction, so the two are exact twins in front elevation.
- The outer wall + facet drop the barely-1 mm reflex kink `pts[3]` (`_outer_poly_pts`) so the SW
  ramp is one straight edge and the `/` is clean. Cavity and plate keep the sharp outline.

There are **no West tunables** — it follows the East crease and the switch positions automatically.
See `_front_slash_crossings` / `_front_facet_mask` and `test_south_mask_two_clean_slashes`.

---

## 3. Phase 2 — shadow-line reveal groove (built, then PARKED 2026-08-01)

Implemented in full, 7 tests green, rendered — then the user decided against it and it was pulled
back out. **The tree carries no groove code.** The complete implementation is parked in the stash:

```
git stash list                     # find the entry by MESSAGE — indices shift as stashes are added
git stash show -p 'stash@{N}'      # review it
git stash apply 'stash@{N}'        # bring it back (docs will conflict — take the tree's version)
```

Notes worth keeping if it is ever revived:

- **The window is 1.4 mm.** Bounded below by the rabbet-pocket ceiling at 6.6 (under it the outer
  skin is only 2.0 mm — the skirt the plate is pushed in and out of) and above by the deep south
  facet toe at 8.0. The plan's 0.8 tall × 0.6 deep at Z 7.0 leaves only 0.2 mm under the toe, which
  reads as a sliver; the version that was built is **0.7 × 0.5 at Z 6.9–7.6**, leaving a 0.4 land.
- **The +Y bump needs its own cutters**, exactly like the rim facet: it stands proud of the nominal
  outline offset, so the polygon ring would carve a buried slot *inside* it rather than a groove on
  its face. The stashed version masks the ring off the bump (`_mcu_bump_exclusion`) and replaces it
  with a north box, a west box and a quadrant-minus-cylinder for the NW corner arc, sharing
  `_bump_facet_south_y()` and a new `_bump_face_frame()` helper so nothing can drift.
- **How it was proved continuous:** comparing the cross-section just below the groove against the
  one inside it pins the removed area to `perimeter × depth`. Measured 99.7% of theoretical across
  508 mm. Targeted probes cannot give you that — they only prove the groove exists where you thought
  to look. Reuse this trick for any future full-perimeter feature.
- On the palm-facing wall the groove necessarily sits right under the facet toe, so the front read
  as "line tucked under the bevel" rather than a 7:9 split. The split only reads on the E/W and back
  elevations.

**Phase 3 is blocked while this is parked** — the filament swap has no line to hide its colour
transition in, so it would leave a visible seam mid-wall.

## 4. Phase 4 — rear tilt riser feet (built, then PARKED 2026-08-01)

Implemented in full, 12 tests green, rendered against a desk line — then parked at the user's request to pick up later. **The tree carries no riser code**; it is a full snapshot in `git stash` (find "Option 8: rear tilt riser feet" in `git stash list`).

What it was: two optional printed pucks per half. They drop into the two REAR rubber-foot seats and lift the
back of the case to a 4° typing angle. Nothing in the tub or the plate changed — leave them off
and the keyboard sits flat exactly as before.

It added `src/sofle_case/feet.py`, a `TILT_*` / `RISER_*` constants block, riser export in
`scripts/build.py` (`--no-risers` to skip), and a `tilt_risers` group in `case.py`'s viewer
block. All of that is in the stash — none of it is in the tree.

### What the geometry has to get right

- **The two risers are different heights, and must be.** The rear seats sit at different Y (110
  west, 104 east), so each column's lift is `tan(tilt) x (y_rear − y_front)` *within that column*
  — 6.15 mm west, 4.62 mm east at 4°. Nothing is hardcoded; change `FOOT_POSITIONS` or
  `TILT_ANGLE_DEG` and the parts follow.
- **The four contacts are then EXACTLY coplanar** — 1.8e-15 mm residual measured on the built
  solids, and it is not luck: with the per-column lift the triple product cancels
  (`t·a·d·Δx − t·a·d·Δx`) for any layout where the two columns share an X. So the case cannot
  rock at any tilt angle. `contact_plane()` asserts it, in case a future edit adds a fifth foot.
- **Each riser's body is `lift − FOOT_DEPTH` tall, not `lift`.** The FRONT pads sit recessed
  0.6 mm inside the plate while the rear pads sit flat under the risers. Miss this and every
  riser stands 0.6 mm proud and the case over-pitches.
- **The stance carries a 0.52° side lean** as well as the 4.000° pitch. That is inherent: the
  FRONT seats are also at different Y (22 vs 38), so the pivot line is oblique in plan and the
  stance is not a pure rotation about X. 0.52° is ≈1.1 mm across the 123 mm foot span. Removing
  it would need a third riser under the front-west seat — judged not worth the extra part.
- **Print orientation:** exported laid flat, tilted ground face down on the bed, spigot up. Full
  Ø12 first layer, no supports. `printable()` reads the ground normal off the solid, so the
  mirrored left-half risers (whose lean is flipped) lay flat with no special-casing.

### The pad-thickness trap — read this before printing

Tilting swings everything FORWARD of the front feet down at the desk, and there is a lot of case
out there: the front seats are at y=22/38 while the thumb-cluster corner reaches y ≈ 0.5. At 4°
that nose drops **1.50 mm**. The only thing holding it up is how far the front pads protrude below
the plate, which is `pad thickness − FOOT_DEPTH`.

The original plan assumed 2.0 mm pads → 1.4 mm protrusion → **the nose grounds by 0.1 mm** before
the feet touch. So `RUBBER_PAD_H` is specified at **3.0 mm** (a stock bumpon size), which clears
the whole supported range:

| tilt | nose clearance on 3.0 mm pads |
|---|---|
| 3° | +1.27 mm |
| 4° | +0.90 mm |
| 5° | +0.53 mm |

> **SUPERSEDED — do not extrapolate this table.** It describes the FEET-BASED tilt design, where
> the case sat flat and rear pads lifted it, so the front nose swung down toward the desk and the
> clearance shrank ~0.37 mm per degree. Extended naively, 7° would read as the nose grounding by
> ~0.2 mm. **That failure mode no longer exists.** Tilt now comes from the BOTTOM CASE being an
> integrated wedge (`TENT_ANGLE_DEG`, `case.tent_wedge`), so the entire underside is a single
> plane coplanar with the desk and the nose is part of it — there is nothing to swing down. The
> foot seats are cut into that plane, so all four pads protrude equally and the clearance is
> uniform at any angle. `RUBBER_PAD_H`, `TILT_ANGLE_DEG` and `feet.desk_clearance()` no longer
> exist anywhere in the source.

`feet.desk_clearance()` measures this against the tessellated solid (the front-most material is a
chamfered corner on an arc-offset wall — not where you would guess), `scripts/build.py` prints it
on every build, and two tests pin it: one that the supported range clears, one that 2.0 mm pads
still fail. If you ever want thinner pads, the levers are a lower `TILT_ANGLE_DEG` (3.7° is the
limit at 2.0 mm) or moving the front `FOOT_POSITIONS` forward — the latter also changes the plain
rubber-foot design and its tests.

### Verified
- Full suite green; both halves + all four risers export clean; every riser a single solid.
- Assembled check (rotate the built halves onto the contact plane, drop a desk line): all four
  contacts touch, pitch measures 4.0000°.

---

## 5. What is left

**Nothing is in flight.** Phase 1 is the only thing in the tree; Phases 2 and 4 are parked in stashes (see above) and Phase 4 is the user's next pick-up when they want it.

**Phase 3 (two-tone filament swap) is blocked** — it keys off the shadow-line groove
to hide the colour transition, and that groove is parked (§3). Unpark the groove or pick a
different line to swap at.

Each phase: implement → `pytest` → build → **user visual verify** → commit.
