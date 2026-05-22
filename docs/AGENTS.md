<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-18 | Updated: 2026-05-18 -->

# docs/

## Purpose
Design reference documentation. Currently one file: the Z-stack reference that is the canonical explanation of every vertical layer in the case.

## Key Files

| File | Description |
|------|-------------|
| `z-stack.md` | Cross-section diagram, layer table, per-layer explanations, standoff geometry table. **Single source of truth for understanding why Z constants have their values.** |

## For AI Agents

### Working In This Directory
- `z-stack.md` must stay in sync with `src/sofle_case/constants.py`. When a Z constant changes, update the table and cross-section diagram here too.
- The layer table lists `Source` column referencing constant names — keep those names accurate.
- Rows above Z=12.0 are **phantom-only** (not structural constants); note that distinction when editing.

### Common Patterns
- Z values in docs always include the constant name in backticks, e.g. `PCB_SEAT_Z = 4.5`.
- ASCII cross-section uses `╌` for phantom/reference lines, `━` for structural boundaries, `▓` for solid material.

<!-- MANUAL: -->
