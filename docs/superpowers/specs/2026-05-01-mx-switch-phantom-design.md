# MX Switch Phantom — Design Spec

**Date:** 2026-05-01
**Branch:** feat/switch-plate-phantom
**Goal:** Add a Cherry MX switch phantom so the OCP viewer shows the complete keyboard stack: case + PCB + plate + all switches + encoder.

---

## Context

Two phantoms already exist and follow an established pattern:

| Module | Part | Z range |
|---|---|---|
| `pcb_phantom.py` | Main PCB + MCU + USB-C stub + slide switch | 4.5 → 10.3 |
| `plate_phantom.py` | Switch plate with cutouts | 9.1 → 10.7 |

The switch phantom is the third and final layer. It is visual-only (not exported to STL/STEP) and gated by `SHOW_SWITCH_PHANTOM` in `constants.py`.

---

## Switch geometry (Cherry MX, simplified for phantom)

Each MX key position renders three stacked primitives:

| Section | Shape | Footprint | Height | Z range |
|---|---|---|---|---|
| Lower housing | Box | 13.8 × 13.8 mm | 3.0 mm | `PLATE_SEAT_Z − 3.0` → `PLATE_SEAT_Z` (9.1) |
| Upper housing | Box | 15.6 × 15.6 mm | 6.6 mm | `PLATE_TOP_Z` (10.7) → 17.3 |
| Stem | Cylinder | Ø4.5 mm | 3.5 mm | 17.3 → 20.8 |

The lower housing sits in the 3 mm MX body clearance gap (PCB top 6.1 → plate seat 9.1). The upper housing and stem protrude above the plate. All three primitives are rotated around Z by the switch's rotation from `components.json`.

---

## Encoder geometry (EC11, SW25)

The encoder occupies the same switch position as `SW_ENCODER_POS`. It renders as two primitives (no rotation needed — shaft is circular):

| Section | Shape | Footprint | Height | Z range |
|---|---|---|---|---|
| Body drum | Cylinder | Ø19 mm | 12.0 mm | `PLATE_TOP_Z` (10.7) → 22.7 |
| Shaft | Cylinder | Ø7 mm | 15.0 mm | 22.7 → 37.7 |

---

## Switch positions

Source: `data/components.json`. Filter rule:
- Key starts with `SW`
- `layer == "top"` (excludes SW31, the slide switch on the bottom layer)

This yields **30 entries**: 29 MX keys + SW25 (encoder position).

SW25 is separated out and rendered as the encoder shape. The remaining 29 are rendered as MX switch shapes.

Two thumb-cluster keys have non-zero rotation: SW26 (−60°), SW27 (23°). Rotation is applied via build123d `Rot(0, 0, angle)` at each switch's case-coord centre.

---

## Module structure

**File:** `src/sofle_case/switch_phantom.py`

```
_load_switch_positions() → list[dict]   # reads components.json, filters top-layer SW*
_mx_switch_solid(cx, cy, rot) → Part   # lower housing + upper housing + stem
_encoder_solid(cx, cy) → Part          # body drum + shaft
build_switch_phantom() → Part          # Part(children=[all MX + encoder])
```

Phantom-only dimension constants (e.g. `_LOWER_H`, `_UPPER_W`) live as module-level names in `switch_phantom.py`, not in `constants.py`. This matches the `pcb_phantom.py` convention.

---

## Constants change

Add to `src/sofle_case/constants.py` (in the phantom section):

```python
SHOW_SWITCH_PHANTOM = False  # True: adds MX switch phantom to case.py __main__ viewer
```

---

## Integration: `case.py` `__main__`

```python
if C.SHOW_SWITCH_PHANTOM:
    from sofle_case.switch_phantom import build_switch_phantom
    parts.append(build_switch_phantom())
    names.append("switch_phantom")
```

---

## Tests: `tests/test_switch_phantom.py`

| Test | Assertion |
|---|---|
| `test_returns_part` | `isinstance(build_switch_phantom(), Part)` |
| `test_z_min_in_gap` | `abs(bb.min.Z - (C.PLATE_SEAT_Z - 3.0)) < 0.2` |
| `test_z_max_above_plate` | `bb.max.Z > C.PLATE_TOP_Z + 6.0` |
| `test_switch_count` | phantom volume is meaningfully larger than a single switch body |

---

## Out of scope

- Keycaps (separate phantom if ever needed)
- Reset button phantom
- OLED phantom
- Export to STL/STEP
