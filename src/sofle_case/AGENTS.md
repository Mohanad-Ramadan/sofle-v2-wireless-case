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
- Phantom modules are visualization-only and must not be imported by structural
  builders.

All geometry uses case coordinates with Z=0 at the printed underside. Preserve
`PCB_TOP_Z == PCB_SEAT_Z + PCB_THICKNESS`, `PLATE_TOP_Z == PLATE_SEAT_Z +
PLATE_THICKNESS`, and `MAIN_RIM_Z == PLATE_TOP_Z`.

Every geometry module keeps optional `ocp_vscode` imports inside its viewer
block. Run `pytest tests/ -x -q` after changes.
