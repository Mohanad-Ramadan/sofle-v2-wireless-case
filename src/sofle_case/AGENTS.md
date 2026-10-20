<!-- Parent: ../AGENTS.md -->

# `src/sofle_case`

The package generates the two reversible Sofle case halves. The sole printable
entry point is `case.build_case_half(side)`, which returns one watertight solid
with a rim flush to the switch plate.

## Geometry ownership

- `constants.py` is the single source of truth for dimensions and Z datums.
- `tray.py` owns the shell, PCB cavity, relief bump, perimeter facets, and the
  protected south chamfer/crease geometry.
- `plate_geometry.py` owns loading the authoritative plate outline and the
  exact nominal plate-fit cutter; `plate_phantom.py` may consume it for viewing.
- `standoffs.py` owns the stepped Ø5.5/Ø3.9 M2 bosses and blind pilot bore.
- `battery.py` owns the battery, JST, and wire-channel recess cutters.
- `cover_mark.py` owns the M17-3 connection-mark plan geometry (pure math; imports
  only the standard library and `constants`). Strokes run out through the cover
  edges. Any mark curve can be a Catmull-Rom through handles (`COVER_MARK_LINE_POINTS` per narrows
  line, `COVER_MARK_CURVE_POINTS` for Bow A; assembled frame, one curve for both covers).
  `catmull_rom` must stay identical to `docs/previews/controller/mark_editor.html`.
  `COVER_MARK_RIGHT_CURVE_LENGTH` limits only the right piece. The narrows fan uses a C1 eased
  ramp (`_eased_ramp`); never go back to `max(x, 0)`, which put a 3-9 deg kink at the entry.
- Phantom modules are visualization-only and must not be imported by structural
  builders.
- OLED modes (`OledMode = "none" | "long" | "short"`): every builder takes a literal
  `oled="none"` default (the OLED phantom and fit report require `long`/`short`) and never
  reads `C.OLED_MODE` at runtime; only the CLI resolves it.
  `none` must stay byte-identical (`tests/test_oled.py` pins volumes and the outline).
  `tray.outline(oled)` and `mcu_encoder_cover.profile(side, oled)` are the cached per-mode
  frames; `C.north_wall_extra(oled)` grows tray segs 12/14 onto one north edge. The window is
  cut last, before the mirror. `oled_phantom.py` owns the module slab and
  `oled_fit_report(side, oled)` (plan §4 labels; physical-frame X; nets derived from
  `C.j3_nets`). Measured, not planned: the short-left tray USB slot starts at y 115.05
  (`TRAY_NORTH_LOW_Y + PCB_XY_CLEARANCE - 1`). The mark is never shifted; it may cross the window.

All geometry uses case coordinates with Z=0 at the printed underside. Preserve
`PCB_TOP_Z == PCB_SEAT_Z + PCB_THICKNESS`, `PLATE_TOP_Z == PLATE_SEAT_Z +
PLATE_THICKNESS`, and `MAIN_RIM_Z == PLATE_TOP_Z`.

Every geometry module keeps optional `ocp_vscode` imports inside its viewer
block. `python -m sofle_case.case [left|right] [none|long|short]` shows
the case, cover and mirrored phantoms (plus the OLED module in OLED modes). Run `pytest tests/ -x -q` after changes.
