# Sofle case Z-stack

All structural Z values are defined in `src/sofle_case/constants.py`, measured
from the flat printed underside (`Z = 0`). The monolithic wall ends flush with
the switch-plate top.

| Datum | Z (mm) | Definition |
|---|---:|---|
| `FLOOR_THICKNESS` | 6.6 | top of the flat case floor |
| `PCB_SEAT_Z` | 9.1 | PCB underside on the standoff shoulder |
| `PCB_TOP_Z` | 10.7 | `PCB_SEAT_Z + PCB_THICKNESS` |
| `PLATE_SEAT_Z` | 14.1 | switch-plate underside |
| `PLATE_TOP_Z` | 15.7 | `PLATE_SEAT_Z + PLATE_THICKNESS` |
| `MAIN_RIM_Z` | 15.7 | `PLATE_TOP_Z` |

The PCB cavity retains `PCB_XY_CLEARANCE` below the plate-fit band. Between
`PLATE_SEAT_Z` and `PLATE_TOP_Z`, the structural cavity is the authoritative
plate outline with exactly zero nominal XY clearance. A grown plate therefore
intersects the fit band, while the nominal plate does not. The full authoritative
MCU opening remains clear throughout this fit band; no printed frame backfills
the notch, so MCU hardware may rise above the plate and printed-case maximum.

Five bosses use a Ø5.5 mm lower shoulder and Ø3.9 mm upper boss. Each reaches
`PLATE_SEAT_Z` and has a blind Ø1.8 mm M2 pilot bore, 4.0 mm deep, with a 0.3 mm
conical entry chamfer. Screws pass through the plate's existing Ø4.1 mm holes.

The internal slide-switch body cavities start at `PCB_TOP_Z - 0.3`. The tray
cavity ends at the modeled can top plus 0.3 mm (15.3 mm); the cover cavity ends
at `MAIN_RIM_Z + 0.3` (16.0 mm). Only the can receives this rectangular internal
clearance. Access comes from one continuous concave port shared by both parts.

The nominal outer rim spans Z=10.4–17.6 mm. At the actuator contact face it
spans Z=10.8–17.2 mm, crossing the tray/cover seam at Z=15.7 mm. Behind the
contact face, the surfaces return smoothly toward the hardware envelope,
screening the can's silhouette without a separate back plate or ledge.
The original nub phantom is the full travel envelope; no additional hardware
sweep is applied.

The cover retains its existing 1.5 mm vertical roof-profile offset. Tests
preserve its actual top millimetre over the access region, the tray's continuous
2 mm floor web, and mounting bosses outside their existing can relief.
Digital phantom clearance does not establish physical pad-only actuation;
check operation on a printed assembly with the roof fitted.

Four rubber-foot recesses open from Z=0 and are `FOOT_DEPTH` deep.

## Build artifacts

Each side exports a monolithic tray STL (`sofle_case_{side}.stl`) and a separate
removable cover STL (`sofle_cover_{side}.stl`). STEP export is unsupported and
removed. Rebuilding a side removes only its exact known legacy monolithic STEP
and split top/bottom artifacts from the requested output directory; unrelated
files are preserved.

## Protected south facet

The south outline grows by `SOUTH_WALL_EXTRA = 3.0` mm before its deep facet is
cut. The facet is a 6.0 mm planar run over an 8.8 mm vertical drop, masked at
`FRONT_FACET_Y_MASK = 22.0` mm. Its east backslash crease and derived mirrored
west slash are retained by `tray._front_slash_crossings`; the rim and toe are
derived from `MAIN_RIM_Z`, never from an independent raised datum.
With the current stack the facet toe is `15.7 - 8.8 = 6.9` mm; the floor
remains at its independent `FLOOR_THICKNESS` datum.
