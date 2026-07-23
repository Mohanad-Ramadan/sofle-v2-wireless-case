# Handoff — Case Aesthetic Refinements (Phase 1 in progress)

**Date:** 2026-07-23
**Branch:** `feat/sandwich-minimal-case` (all changes below are **UNCOMMITTED**)
**Full plan:** `.omc/plans/2026-07-23-case-aesthetic-refinements.md` (4 phases)
**Status:** Phase 1 (rim facet) implemented + tests pass (131), **but one SW-corner cosmetic
issue is UNRESOLVED** — the user still sees two creases on the SW thumb wall and wants one.
Phases 2–4 not started.

---

## 0. Environment / commands (this repo)

- Python venv: **`.venv/bin/python`** (build123d 0.10.0). System `python`/`python3` do NOT have build123d.
- Run tests: `.venv/bin/python -m pytest -q` (~170 s, currently **131 passed**).
- Build/export a half: `.venv/bin/python scripts/build.py right` → writes
  `output/sofle_{right,left}_{top,bottom}.{stl,step}`. The shipped design is the **sandwich**
  (TOP tub + BOTTOM plate); `build_case_half` is a legacy single-piece tray behind `--legacy`.
- **Offline renders (no interactive OCP viewer needed)** — helper scripts copied to `scripts/dev/`:
  - `render.py <stl> <out.png>` — 3 whole-part views.
  - `section.py <stl> <out.png>` — Y-Z cross-sections at X=40 and X=80 (proves front height).
  - `render_corner.py <stl> <out.png> <xlo> <xhi> <ylo> <yhi> "title"` — zoomed, clean
    (full-triangle clip). SW corner crop used: `0 50 -3 42`.
  - Example: `.venv/bin/python scripts/dev/render_corner.py output/sofle_right_top.stl /tmp/sw.png 0 50 -3 42 "SW"`

---

## 1. Fixed geometry facts (verified against `constants.py`)

| Fact | Value | Note |
|---|---|---|
| Tub rim (sandwich TOP) | `COVER_TOP_Z = 16.0` | inline "13.5" comments in constants are STALE; real value 16.0 |
| Legacy tray rim | `MAIN_RIM_Z = 15.0` | `build_tray()` default |
| Wall thickness | `WALL_THICKNESS = 4.75` | envelope derives from it |
| Rabbet ledge | `SEAM_LEDGE_Z = 6.3` | split height |
| Outer skin below ledge | `SEAM_SKIN = 2.0` | **exterior bites below Z=6.3 must be ≤0.5 mm** (rabbet pocket behind skin) |
| Membrane fuse band | inner `COVER_FUSE_MARGIN = 1.0` of wall | facet must not reach it |
| Pocket cutter top | `SEAM_LEDGE_Z + SEAM_LEDGE_CLEAR = 6.6` | groove (Phase 2) must clear this |
| OCC rejects asymmetric `chamfer()` on the rim edge set | — | facets MUST be cutter solids, not `chamfer()` |

The TOP is a deep tub that owns the full outer skin to the ground (no outer seam). `build_tray(rim_z)`
builds the outer shell + cavity + MCU +Y relief bump, and is called by both `build_case_half`
(rim 15) and `build_top_part` (rim 16, then adds membrane/encoder/canopy, then cuts the slide scoop).

### South (palm-facing) outline, case coords (inner polygon; outer wall = +5.25 offset, Kind.ARC)
South-facing edges (`polygon_in_case_coords()`, 18-pt CCW polygon):
- **E0** (5.2, 30.2) → (19.8, 5.2)   — SW **thumb wall**, normal ≈ (−0.87, −0.5) (half-south/half-west)
- **E1** (19.8, 5.2) → (36.8, 15.2)  — ramp1 (the pointy bottom is vertex (19.8, 5.2))
- **E2** (36.8, 15.2) → (54.2, 23.2) — ramp2
- **E3** (54.2, 23.2) → (110.8, 23.2)— central front, normal (0, −1)  (the long 56 mm span, y=23.2)
- **E4** (110.8, 23.2) → (148.8, 33.2)— SE ramp
- West wall starts at case-y ≈ 24.75; E/W walls face ±X (not south).

---

## 2. What Phase 1 implemented (the drafted rim facet)

Goal: the 16 mm flat wall read as an ugly tall slab. Replace the old shallow 1.9 mm 45° outer-top
chamfer with a **drafted facet** all round (shallow) + a **deeper, aggressive facet on the
palm-facing south run** so the front reads ~half height (premium-alloy-board look). Prints
support-free: the tub prints top-face-down → facets become 20–27° overhangs.

### `constants.py` — new facet block (after the "Snap aids DEFERRED" comment, ~line 132)
```
RIM_FACET_DROP     = 4.0    # perimeter facet vertical extent (Z = rim → rim−4)
RIM_FACET_RUN      = 2.0    # perimeter inset at rim (~27° from vertical); rim wall left = 2.75
FRONT_FACET_DROP   = 8.0    # south facet vertical extent (Z = rim → rim−8): tall dominant bevel
FRONT_FACET_RUN    = 3.0    # south inset at rim (~21° from vertical); rim wall left = 1.75
FRONT_FACET_Y_MASK = 24.0   # case-Y north limit of south facet on central/SE front
FRONT_FACET_SW_STEP_X = 20.0  # case-X where the mask steps up on the SW  (added for the SW fix attempt)
FRONT_FACET_SW_Y_MASK = 28.0  # case-Y north limit on the SW (covers thumb wall to its top corner)
```
Plus 4 import-time `assert` guards (≥1.5 mm rim wall, clears fuse band, south toe ≥ SEAM_LEDGE_Z+1).
`OUTER_TOP_CHAMFER = 1.9` is KEPT (canopy.py reads it as a wall-inset offset) but is no longer
applied to the rim.

### `tray.py`
- Added `loft` to the build123d import line.
- New helpers:
  - `_rim_facet_frustum(drop, run, rim_z)` — lofts between two concentric Kind.ARC polygon offsets
    (outer wall at the toe Z=rim−drop, inset by `run` at the rim). Extended ±0.6 past toe/rim so
    the wedge cutter has no coincident cap faces.
  - `_rim_facet_cutter(drop, run, rim_z)` — `offset_extruded(outer band) − frustum` = wedge ring,
    zero-width at the toe, `run` wide at the rim. Subtract it → drafted facet.
  - `_mcu_bump_exclusion(rim_z)` — box over the +Y relief bump (north wall, x 8.5–54.75,
    y≥121) subtracted from the PERIMETER cutter so the proud bump keeps a square top (the
    nominal-offset facet would slice a notch through it).
  - `_front_facet_mask()` — **plan REGION** (extruded polygon) selecting where the DEEP facet
    applies: north limit `FRONT_FACET_Y_MASK` across central/SE, stepping up to
    `FRONT_FACET_SW_Y_MASK` for `x < FRONT_FACET_SW_STEP_X` (the SW). Intersected with the deep cutter.
  - `_apply_rim_facets(part, rim_z)` — `part − (perim − bump_exclusion) − (deep_cutter & mask)`.
- `build_tray()` — replaced `_chamfer_outer_top_edges(hollow, rim_z)` with
  `_apply_rim_facets(hollow, rim_z)` (same position: after concave/bump-corner fillets, before
  bottom chamfer). **Deleted** the now-dead `_chamfer_outer_top_edges` function.

### `tests/test_rim_facet.py` (NEW, 6 tests, all pass)
single-solid at both rims; constant guards; south cut present; perimeter cut present; **SW mask
steps up**; MCU bump excluded.

### Verified working
- `build_tray` valid single solid at rim 15 and 16; export clean; full suite 131 passed.
- Point probes on arc-offset walls are UNRELIABLE (exact wall X/Y is hard to hand-compute through
  the Kind.ARC offset). **Use the render scripts, not point probes, to judge geometry.**

---

## 3. THE UNRESOLVED ISSUE — SW thumb-wall creases (user rejected current state)

### What the user wants
The palm-facing south wall should have the aggressive deep facet. Where the deep south facet meets
the shallower perimeter facet, a crease is unavoidable. On the **SE** corner this transition crease
"looks very good by accident" (it tucks into the SE corner) — **keep SE as-is**. On the **SW** the
user wants **exactly ONE crease** on the thumb wall — an *angled* one (a facet-intersection at a
plan corner), NOT the horizontal "straight" crease that a flat Y=mask plane slices across the wall.
User's words: "keep the angled one on SW but relocate it at the removed straight crease, so the
angled does both crease purposes."

### Why there are two creases (root-cause geometry)
A crease appears at every point where two facet surfaces of different slope/direction meet:
- **(19.8, 5.2)** — vertex between E1 and E0 (the pointy bottom of the thumb): facet-intersection
  → an **angled** crease. This is the one the user *likes*.
- A **deep→shallow transition** crease wherever the deep-facet mask ends on the thumb wall.

**Original state (flat `FRONT_FACET_Y_MASK=24` half-plane):** deep facet ended mid-E0 at ~(8.8, 24)
→ a **horizontal "straight" crease** across the thumb wall (visible because E0 rises steeply, so the
Y=24 plane cuts it high/in the open). Two creases: angled@(19.8,5.2) + straight@mid-E0.

**My attempted fix (current code, `FRONT_FACET_SW_Y_MASK=28`, step at x=20):** extended the deep
facet UP the whole thumb wall so the transition moved to the top corner **(5.2, 30.2)** where E0
meets the west wall. This removed the *horizontal* crease but created a NEW angled crease at
(5.2, 30.2). **Net: still two creases** — angled@(19.8,5.2) + angled@(5.2,30.2). User still sees two.
**This is the current, rejected state.**

### The real problem
The SW thumb wall E0 is bounded by two plan corners — (19.8,5.2) at the bottom and (5.2,30.2) at
the top. If E0 is deep-faceted, BOTH corners produce a crease against their neighbours (E1 deep,
west shallow). If E0 is shallow-faceted, the crease moves to (19.8,5.2) only (E1 deep vs E0
shallow) and (5.2,30.2) becomes shallow-vs-shallow (minimal). Getting to **one** crease likely
needs one of:

1. **Bottom-point reading (simplest, untried):** make E0 (thumb wall) **shallow** like the west
   wall, so the ONLY SW crease is the angled one at the bottom point (19.8,5.2) between deep E1 and
   shallow E0. Try: mask excludes E0 (e.g. `FRONT_FACET_SW_Y_MASK` LOWER than the E0 span, or a mask
   that stops at the E1 start near x≈20). Risk: user earlier said "relocate up at the straight
   crease" which sounded like the top — but they've since rejected the top version, so bottom-point
   is the leading candidate. **Confirm with the user before building.**
2. **Fillet/round one crease away** — apply a 3-D fillet along the unwanted facet-intersection edge
   so only one reads. Fragile in OCC on these blended arc faces.
3. **Single swept draft on the SW** — instead of per-segment planar facets, sweep one continuous
   drafted surface around the SW arc corners so there is no planar break (no crease) except the one
   desired. More work; most robust visually.
4. **Coincide the two creases** — choose facet params so the deep→shallow transition falls exactly
   on (19.8,5.2), merging with the liked angled crease. Requires the mask boundary to pass through
   that vertex.

**Recommended next step:** show the user a render of option 1 (thumb wall shallow, one crease at
the bottom point) and, if rejected, option 3. Always verify with `scripts/dev/render_corner.py`
(crop `0 50 -3 42`), not point probes.

---

## 4. Remaining phases (not started) — from the plan

- **Phase 2 — shadow-line reveal groove:** 0.8 tall × 0.6 deep ring at Z 7.0–7.8 (above the 6.6
  pocket top, below the south facet toe at 8.0). Cutter = `_outer_extruded` ring minus inset offset;
  reuse the MCU-bump handling. Splits the elevation ~7:9.
- **Phase 3 — two-tone filament-swap doc:** no geometry; `docs/two-tone-print.md` + build.py prints
  the swap Z for both print orientations, keyed to the groove mid-line.
- **Phase 4 — rear tilt riser feet:** separate parts (`feet.py`), 3–5°. NOTE the trap: rear
  `FOOT_POSITIONS` sit at different Y (110 vs 104) → per-seat riser heights derived from
  `FOOT_POSITIONS`+angle (4° ≈ 6.15 mm left, 4.61 mm right); bottoms cut by one shared tilted plane
  so no rock. Case bodies unchanged.

Each phase: implement → `pytest` → build → **user visual verify in render/OCP viewer** → commit.

---

## 5. Exact current diff (uncommitted)
```
 M src/sofle_case/constants.py   (+35: facet block + SW mask consts + guards)
 M src/sofle_case/tray.py        (+116/−46: facet helpers, build_tray rewire, deleted _chamfer_outer_top_edges)
?? tests/test_rim_facet.py       (new, 6 tests)
?? scripts/dev/                  (render tools: render.py, section.py, render_corner.py)
?? docs/2026-07-23-handoff-aesthetic-refinements.md  (this file)
```
Nothing committed. The user gates each commit on visual approval. **Phase 1 is NOT approved** — the
SW crease (§3) must be resolved first.
