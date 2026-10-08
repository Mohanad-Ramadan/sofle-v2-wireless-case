# Sofle V2 Wireless Case

Parametric build123d generator for the Sofle V2 Wireless (Alt_Switch). Each
reversible half is a single surface-less monolithic tray: the rim ends exactly
at the switch-plate top, with integrated tapped bosses, battery/JST recesses,
slide-switch access, and rubber-foot seats.

The nominal PCB-to-inner-wall clearance is **0.40 mm per side**, with **4.75 mm**
structural walls. Printed fit still requires checking against the actual PCB.

## Build

```sh
source .venv/bin/activate
python scripts/build.py left
python scripts/build.py right
```

Each command writes `output/sofle_case_{side}.stl` and the separate removable
`output/sofle_cover_{side}.stl`. STEP export is unsupported and has been removed.
When rebuilding, the CLI removes only the exact known legacy monolithic STEP
and split top/bottom artifacts for the requested side; unrelated files are
preserved. Use `--show` to open the viewer and add
`--phantoms` to include the hardware; phantoms are never fused or exported.

## Test

```sh
ruff check .
pytest tests/ -x -q
```

The authoritative vertical stack and the protected south facet dimensions are
documented in [docs/z-stack.md](docs/z-stack.md) and defined in
`src/sofle_case/constants.py`.

## Battery pocket and wire retention

The battery pocket is **51 × 73 mm (X × Y)** for a **50 × 72 mm** cell
including its protection circuit, with 0.5 mm clearance per side. Its depth
is unchanged; use adhesive on the flat floor rather than battery clips.
The assumed cell thickness remains 4.5 mm; thicker cells need a Z-clearance check.

The **5 mm-wide hooked wire trench** keeps its route and has **1.5 mm-radius
lower corners**. Continuous lips run along both sides, including the turns,
leaving a **1.5 mm-wide top insertion slot** for **1 mm-diameter insulated leads**.
The lips are 1.2 mm thick and flush with the floor top, leaving a **3.3 mm-high
lower cavity** for loose bends and excess wire. The top slot has 0.375 mm-radius
corners; both pocket entrances remain open. Insert leads individually through
the slot and tuck slack beneath the lips without tight folds or insulation
compression. Printed lip strength, overhang quality, and adhesive fit still
need a physical check.

## MCU cover south edge

The removable cover has a **17 mm-wide, 4 mm-deep faceted south recess**,
with a **6 mm flat central lip**, diagonal sides, **1.5 mm clipped outer
corners**, and a **0.5 mm top bevel**. The bevel wraps around both south
corners and continues along the low side edges. Across the ramp, a single
ruled Bezier surface gradually changes from the south bevel's **45°**
section to the side chamfer's **2:1 draft (63.4°)**. Width and drop follow
smoothstep profiles with zero longitudinal derivatives at both ends;
there is no overlapping-cut ridge or abrupt change of angle.
Normally offset cavity facets preserve the **1.5 mm south wall**; the
inner lip remains **0.5 mm clear of the encoder plate-window envelope**.

Adjust `COVER_RECESS_DEPTH`, `COVER_RECESS_HALF_WIDTH`, and
`COVER_RECESS_FLAT_HALF_WIDTH` in `src/sofle_case/constants.py`.
Reducing depth moves the shoulders inward without moving the central lip
or sacrificing wall thickness or clearance. Both halves mirror the recess.
Physical fit still needs a printed check.

## MCU cover connection mark

The removable MCU/encoder covers carry the approved **M17-3** connection mark
on their roofs: three narrows lines plus one steep bow curve, engraved
**0.80 mm wide and 0.30 mm deep** (the roof keeps 1.20 mm). The figure is
drawn once in the assembled pair frame, so the left and right covers each
carry a different piece of the same figure; the footprints still mirror.
Like the old canopy marks, the grooves run out through the cover's edges:
each holds its full depth to the chamfer's top line, then dies away as the
chamfer drops below the groove floor. Only the encoder shaft margin and the
USB opening are kept clear.

Every mark curve is fully editable. `COVER_MARK_LINE_POINTS` (one entry per
narrows line, south to north) and `COVER_MARK_CURVE_POINTS` (Bow A) hold
handles in the assembled pair frame; each edited curve is one centripetal
Catmull-Rom through its handles, so both covers cut smooth, continuous pieces
of it through the gap. `None` keeps that curve's formula.
`COVER_MARK_RIGHT_CURVE_LENGTH` limits how far the right cover's Bow A piece
runs from its north entry (`None` = out through the edge). Edit them visually
in `docs/previews/controller/mark_editor.html` (serve that folder, e.g.
`python -m http.server --directory docs/previews/controller`): pick a curve,
drag its handles, double-click it to add a handle, or tick "Keep left cover
unchanged" to lock the handles that shape the left piece. The readout lists
where every curve exits the right cover's east edge and the gaps between them.
Download its JSON, then `python scripts/dev/mark_editor.py apply mark.json` and
rebuild. Re-run `python scripts/dev/mark_editor.py export` after any other
`COVER_MARK_*` change so the page stays in sync.

The narrows lines' fan eases in over `COVER_MARK_FAN_BLEND` (6 mm) either side
of the squeeze point, so the lines enter the right cover without a kink.

Tune `COVER_MARK_*` in `src/sofle_case/constants.py`. Set
`COVER_MARK_ENABLED = False` (or pass `mark=False`) to build plain covers.
Widen `COVER_MARK_WIDTH` and `COVER_MARK_CURVE_WIDTH` together if the test
print is faint. The geometry lives in `src/sofle_case/cover_mark.py`
(pure plan math) and `_mark_cutter` in `src/sofle_case/mcu_encoder_cover.py`.

## Slide-switch access

The tray and mounted MCU cover share **one concave, jack-like port** with a
rounded rectangular outline. Its nominal outer rim is 12 × 7.2 mm, with
10 × 6.4 mm clearance at the actuator contact face. The floor and sides curve
continuously into the rear hardware clearance: no flat back-wall ledge,
nested slot, or abrupt second step. The cover roof remains closed.

The unchanged nub phantom represents the entire actuator travel. This port
allows localized fingertip-pad contact, not entry of a whole finger. Tests
use a 5 × 4 mm contact patch with at least 0.3 mm clearance shifting across
that face, plus a separate check that the mounted cover is actually relieved.
Physical pad-only switching and comfort still need a printed-assembly check.
