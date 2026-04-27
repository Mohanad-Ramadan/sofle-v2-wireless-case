# Sofle V2 Wireless Case Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a parametric Build123d Python project that produces left+right tray-case STL/STEP files for the Sofle V2 Wireless (Alt_Switch) keyboard from PCB GERBER/drill/CPL data.

**Architecture:** Single-source-of-truth `constants.py` drives geometry. GERBER `EdgeCuts` is parsed once into a JSON polygon; that polygon plus the 5 PTH mounting holes drives the inner cavity and standoff positions. Build123d composes outer shell, hollow cavity, 5 stepped standoffs, raised MCU cover (merged with +Y wall), and wall/floor cutouts. A `mirror(plane="YZ")` produces the right half from the left.

**Tech Stack:** Python 3.11+, build123d ≥ 0.7, pytest, numpy, click (CLI). No CAD GUI dependency.

**Repo root:** `/Users/mohanadramadan/Documents/SPK Builds/Sofle/3D prints/My Sofle Case/`

**Source PCB data location (read-only inputs):**
- GERBER zip: `/Users/mohanadramadan/Documents/SPK Builds/Sofle/Wireless Sofle/Alt_Switch/GERBER-SofleKeyboard.zip`
- CPL: `/Users/mohanadramadan/Documents/SPK Builds/Sofle/Wireless Sofle/Alt_Switch/CPL-SofleKeyboard.csv`

---

## File Structure

All paths relative to repo root.

| File | Responsibility |
|------|----------------|
| `pyproject.toml` | Package metadata + deps |
| `.gitignore` | Ignore `output/`, `__pycache__/`, `.venv/` |
| `README.md` | Short user guide |
| `AGENT.md` | Build/modify workflow for agents |
| `src/sofle_case/__init__.py` | Package marker |
| `src/sofle_case/constants.py` | All dimensions (single source of truth) |
| `src/sofle_case/pcb_geometry.py` | Loads cached PCB polygon JSON; offset helper |
| `src/sofle_case/components.py` | Loads cached CPL JSON |
| `src/sofle_case/tray.py` | Outer shell + inner cavity + top chamfer |
| `src/sofle_case/standoffs.py` | One stepped standoff at (x,y) |
| `src/sofle_case/mcu_cover.py` | Raised MCU enclosure merged with +Y wall |
| `src/sofle_case/cutouts.py` | USB-C, slide-switch slot, reset pinhole, floor recess |
| `src/sofle_case/case.py` | Composes all parts; `build_case_half(side)` entry |
| `scripts/parse_gerber.py` | One-off: GERBER zip → `data/pcb_outline.json` + `data/mounting_holes.json` |
| `scripts/parse_cpl.py` | One-off: CPL csv → `data/components.json` |
| `scripts/build.py` | CLI: `python scripts/build.py {left|right}` → STL+STEP |
| `data/pcb_outline.json` | Cached ordered (x,y) polygon vertices |
| `data/mounting_holes.json` | Cached `[(x,y), …]` list |
| `data/components.json` | Cached component positions dict |
| `tests/test_constants.py` | Sanity (envelope ≥ PCB+walls; Z stack monotonic) |
| `tests/test_pcb_geometry.py` | Polygon closed; bbox matches spec |
| `tests/test_holes.py` | 5 holes parsed; positions match spec ±0.01mm |
| `tests/test_standoff.py` | Standoff has correct OD/ID/Z |
| `tests/test_case.py` | `build_case_half` returns Solid; bbox correct; mirror works |
| `output/` | Build artifacts (gitignored) |

---

## Task 1: Project Scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `README.md`
- Create: `AGENT.md`
- Create: `src/sofle_case/__init__.py`
- Create: `tests/__init__.py`
- Create: `data/.gitkeep`
- Create: `output/.gitkeep`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "sofle-case"
version = "0.1.0"
description = "Parametric 3D-printed tray case for Sofle V2 Wireless"
requires-python = ">=3.11"
dependencies = [
    "build123d>=0.7.0",
    "numpy>=1.26",
    "click>=8.1",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-cov>=5.0"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

- [ ] **Step 2: Create `.gitignore`**

```
__pycache__/
*.pyc
.venv/
.pytest_cache/
output/
*.stl
*.step
.coverage
```

- [ ] **Step 3: Create `src/sofle_case/__init__.py` and `tests/__init__.py`** (both empty files)

- [ ] **Step 4: Create `data/.gitkeep` and `output/.gitkeep`** (both empty)

- [ ] **Step 5: Create `README.md`**

```markdown
# Sofle V2 Wireless Case

Parametric tray case generator for the Sofle V2 Wireless (Alt_Switch) keyboard.

## Build

```
python -m venv .venv && source .venv/bin/activate
pip install -e .[dev]

# One-off: extract dimensions from PCB sources
python scripts/parse_gerber.py /path/to/GERBER-SofleKeyboard.zip
python scripts/parse_cpl.py /path/to/CPL-SofleKeyboard.csv

# Build case halves
python scripts/build.py left
python scripts/build.py right
```

Outputs: `output/sofle_case_{left,right}.{stl,step}`

## Test

```
pytest
```

See `docs/superpowers/specs/2026-04-25-sofle-v2-wireless-case-design.md` for full spec.
```

- [ ] **Step 6: Create `AGENT.md`**

```markdown
# Agent Handoff

All dimensions live in `src/sofle_case/constants.py`. Change there; rebuild with `python scripts/build.py {left,right}`. Run `pytest` after every change.

PCB-derived data is cached as JSON in `data/`. Re-run `scripts/parse_gerber.py` only if the PCB sources change.

Build sequence: see `src/sofle_case/case.py::build_case_half`.
```

- [ ] **Step 7: Create venv and install**

Run: `python -m venv .venv && source .venv/bin/activate && pip install -e .[dev]`
Expected: install succeeds; `pytest --version` works.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml .gitignore README.md AGENT.md src/ tests/ data/.gitkeep output/.gitkeep
git commit -m "scaffold: package layout, deps, gitignore"
```

---

## Task 2: Constants Module + Sanity Tests

**Files:**
- Create: `src/sofle_case/constants.py`
- Create: `tests/test_constants.py`

- [ ] **Step 1: Write failing test `tests/test_constants.py`**

```python
"""Sanity checks on dimension constants."""
from sofle_case import constants as C


def test_z_stack_monotonic():
    """Z layers must increase: floor < pcb_seat < pcb_top < plate_seat < plate_top < rim < mcu_cover."""
    z = [
        C.FLOOR_THICKNESS,
        C.PCB_SEAT_Z,
        C.PCB_TOP_Z,
        C.PLATE_SEAT_Z,
        C.PLATE_TOP_Z,
        C.MAIN_RIM_Z,
        C.MCU_COVER_Z,
    ]
    assert z == sorted(z), f"Z stack not monotonic: {z}"


def test_pcb_thickness_consistent():
    assert C.PCB_TOP_Z - C.PCB_SEAT_Z == C.PCB_THICKNESS


def test_plate_thickness_consistent():
    assert C.PLATE_TOP_Z - C.PLATE_SEAT_Z == C.PLATE_THICKNESS


def test_outer_envelope_fits_pcb():
    PCB_W, PCB_D = 143.5, 115.5
    assert C.OUTER_WIDTH >= PCB_W + 2 * C.WALL_THICKNESS + 2 * C.PCB_XY_CLEARANCE
    assert C.OUTER_DEPTH >= PCB_D + 2 * C.WALL_THICKNESS + 2 * C.PCB_XY_CLEARANCE


def test_standoff_passes_pcb_hole():
    assert C.STANDOFF_OD_UPPER < C.PCB_HOLE_DIA
    assert C.STANDOFF_OD_LOWER > C.PCB_HOLE_DIA  # shoulder must catch PCB


def test_five_mounting_holes():
    assert len(C.MOUNTING_HOLES) == 5
```

- [ ] **Step 2: Run; verify ImportError**

Run: `pytest tests/test_constants.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sofle_case.constants'`

- [ ] **Step 3: Create `src/sofle_case/constants.py`**

```python
"""All dimensions in mm. Single source of truth for the case geometry.

See docs/superpowers/specs/2026-04-25-sofle-v2-wireless-case-design.md.
"""

# ---------- Heights (Z = 0 at case bottom) ----------
FLOOR_THICKNESS = 2.0
PCB_SEAT_Z      = 4.5
PCB_TOP_Z       = 6.1   # PCB_SEAT_Z + PCB_THICKNESS
PLATE_SEAT_Z    = 6.5
PLATE_TOP_Z     = 8.0   # PLATE_SEAT_Z + PLATE_THICKNESS
MAIN_RIM_Z      = 10.0
MCU_COVER_Z     = 17.0

PCB_THICKNESS   = 1.6
PLATE_THICKNESS = 1.5

# ---------- Outer envelope ----------
OUTER_WIDTH     = 162.0
OUTER_DEPTH     = 131.0
WALL_THICKNESS  = 3.0
CORNER_RADIUS   = 3.5
TOP_CHAMFER     = 1.5

# ---------- Standoff geometry ----------
STANDOFF_OD_LOWER  = 5.5   # PCB-seat shoulder OD
STANDOFF_OD_UPPER  = 3.5   # passes through PCB Ø4.1 hole
STANDOFF_TAP_DIA   = 1.6   # M2 self-tap bore
STANDOFF_TAP_DEPTH = 4.0

# ---------- Clearances ----------
PCB_XY_CLEARANCE = 0.5
PCB_HOLE_DIA     = 4.1

# ---------- Optional perimeter PCB ledge (default off; see spec §3.4) ----------
PCB_LEDGE_ENABLED = False
PCB_LEDGE_WIDTH   = 1.0   # mm; ring width if enabled

# ---------- MCU cover ----------
MCU_COVER_W = 23.0
MCU_COVER_D = 40.0

# ---------- Cutouts (W = horizontal width along wall, H = vertical height) ----------
USB_C_W, USB_C_H = 9.0, 4.0
USB_C_Z_CENTER   = 14.0

SLIDE_SWITCH_W, SLIDE_SWITCH_H = 6.0, 3.5
SLIDE_SWITCH_Z_RANGE = (1.0, 4.5)

RESET_PIN_DIA  = 2.0
RESET_Z_CENTER = 7.5

SLIDE_SWITCH_RECESS_W     = 10.0
SLIDE_SWITCH_RECESS_D     = 5.0
SLIDE_SWITCH_RECESS_DEPTH = 1.5

# ---------- Component positions (PCB coords, mm) ----------
MCU_POS        = (10.27, -16.16)
SW_SLIDE_POS   = (2.945, -43.23)
SW_RESET_POS   = (7.72,  -45.35)
SW_ENCODER_POS = (9.47,  -65.95)
J_OLED_POS     = (5.22,  -33.69)

# ---------- PTH mounting holes (PCB coords, mm); from SofleKeyboard-PTH.drl T9 Ø4.1 ----------
MOUNTING_HOLES = [
    (14.07,  -80.26),
    (39.57,  -19.05),
    (39.57,  -56.96),
    (116.07, -25.66),
    (116.07, -63.96),
]

# ---------- PCB → case coordinate transform ----------
# PCB X range: -8.5 .. 135.0 (width 143.5); Y range: -110.5 .. 5.0 (depth 115.5).
# Case origin (0,0) is the case OUTER lower-left corner. PCB is centered in case.
PCB_X_MIN, PCB_X_MAX = -8.5, 135.0
PCB_Y_MIN, PCB_Y_MAX = -110.5, 5.0

PCB_OFFSET_X = (OUTER_WIDTH - (PCB_X_MAX - PCB_X_MIN)) / 2 - PCB_X_MIN
PCB_OFFSET_Y = (OUTER_DEPTH - (PCB_Y_MAX - PCB_Y_MIN)) / 2 - PCB_Y_MIN


def pcb_to_case(x: float, y: float) -> tuple[float, float]:
    """Translate a PCB-coordinate point into case (outer-rect) coordinates."""
    return (x + PCB_OFFSET_X, y + PCB_OFFSET_Y)
```

- [ ] **Step 4: Run; verify pass**

Run: `pytest tests/test_constants.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/sofle_case/constants.py tests/test_constants.py
git commit -m "constants: dimensions + PCB→case transform with sanity tests"
```

---

## Task 3: Extract PCB Sources Into Repo

**Files:**
- Create: `data/raw/SofleKeyboard-EdgeCuts.gbr` (extracted)
- Create: `data/raw/SofleKeyboard-PTH.drl` (extracted)
- Create: `data/raw/CPL-SofleKeyboard.csv` (copied)

The GERBER zip lives in `~/Documents/SPK Builds/Sofle/Wireless Sofle/Alt_Switch/GERBER-SofleKeyboard.zip`. We extract only the two files we need plus the CPL.

- [ ] **Step 1: Make raw dir**

Run: `mkdir -p data/raw`

- [ ] **Step 2: List zip contents to confirm filenames**

Run: `unzip -l "/Users/mohanadramadan/Documents/SPK Builds/Sofle/Wireless Sofle/Alt_Switch/GERBER-SofleKeyboard.zip" | grep -E "EdgeCuts|PTH"`
Expected: lists `SofleKeyboard-EdgeCuts.gbr` and `SofleKeyboard-PTH.drl` (paths may have a folder prefix; note exact names).

- [ ] **Step 3: Extract the two files**

Run: `unzip -j -o "/Users/mohanadramadan/Documents/SPK Builds/Sofle/Wireless Sofle/Alt_Switch/GERBER-SofleKeyboard.zip" "*EdgeCuts.gbr" "*PTH.drl" -d data/raw/`
Expected: 2 files extracted to `data/raw/`.

- [ ] **Step 4: Copy CPL**

Run: `cp "/Users/mohanadramadan/Documents/SPK Builds/Sofle/Wireless Sofle/Alt_Switch/CPL-SofleKeyboard.csv" data/raw/`
Expected: file copied; `ls data/raw/` shows 3 files.

- [ ] **Step 5: Verify file contents quickly**

Run: `head -20 data/raw/SofleKeyboard-EdgeCuts.gbr`
Expected: GERBER header lines (`%FSLAX...`, `G04 ...`, etc).

Run: `head -3 data/raw/SofleKeyboard-PTH.drl`
Expected: drill header (`M48`, `;FILE_FORMAT=...`).

- [ ] **Step 6: Commit raw data**

```bash
git add data/raw/
git commit -m "data: vendored EdgeCuts gerber, PTH drill, CPL"
```

---

## Task 4: GERBER → Polygon Parser

**Files:**
- Create: `scripts/parse_gerber.py`
- Create: `tests/test_parse_gerber.py`
- Generates: `data/pcb_outline.json`, `data/mounting_holes.json`

**Approach:** The EdgeCuts gerber uses absolute coordinates with a format header `%FSLAX46Y46*%` (4 integer + 6 fractional digits, units mm via `%MOMM*%`). Each `D02` is a pen-up move to the listed coordinate; each `D01` is a draw to the listed coordinate. We parse the segments, build an adjacency map keyed by (rounded-to-µm) endpoints, then walk the loop. The PTH drill file uses Excellon format; we read T9 (Ø4.1mm) coordinates.

- [ ] **Step 1: Write failing test `tests/test_parse_gerber.py`**

```python
"""Tests for GERBER + drill parsers."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_parse_gerber_produces_outline_and_holes(tmp_path):
    """Parser must emit pcb_outline.json (closed polygon) and mounting_holes.json (5 entries)."""
    out_dir = tmp_path / "data"
    out_dir.mkdir()
    gbr = ROOT / "data" / "raw" / "SofleKeyboard-EdgeCuts.gbr"
    drl = ROOT / "data" / "raw" / "SofleKeyboard-PTH.drl"
    assert gbr.exists() and drl.exists()

    script = ROOT / "scripts" / "parse_gerber.py"
    subprocess.run(
        [sys.executable, str(script), str(gbr), str(drl), "--out", str(out_dir)],
        check=True,
    )

    outline = json.loads((out_dir / "pcb_outline.json").read_text())
    holes = json.loads((out_dir / "mounting_holes.json").read_text())

    assert isinstance(outline, list)
    assert len(outline) >= 6  # PCB outline has at least 6 vertices
    assert outline[0] == outline[-1], "polygon must be closed (first == last)"

    # Bbox check (per spec §2.1)
    xs = [p[0] for p in outline]
    ys = [p[1] for p in outline]
    assert abs(min(xs) - (-8.5)) < 0.05
    assert abs(max(xs) - 135.0) < 0.05
    assert abs(min(ys) - (-110.5)) < 0.05
    assert abs(max(ys) - 5.0) < 0.05

    assert len(holes) == 5
    expected = {
        (14.07, -80.26),
        (39.57, -19.05),
        (39.57, -56.96),
        (116.07, -25.66),
        (116.07, -63.96),
    }
    got = {(round(x, 2), round(y, 2)) for x, y in holes}
    assert got == expected
```

- [ ] **Step 2: Run; verify fail**

Run: `pytest tests/test_parse_gerber.py -v`
Expected: FAIL — `scripts/parse_gerber.py` does not exist.

- [ ] **Step 3: Create `scripts/parse_gerber.py`**

```python
"""Parse SofleKeyboard EdgeCuts GERBER + PTH drill into JSON.

Usage:
    python scripts/parse_gerber.py <edgecuts.gbr> <pth.drl> [--out data/]
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path
from collections import defaultdict
import click


# ---------- GERBER ----------

_FS_RE = re.compile(r"%FSLAX(\d)(\d)Y(\d)(\d)\*%")
_COORD_RE = re.compile(r"X(-?\d+)Y(-?\d+)D0([12])\*")


def _parse_format(text: str) -> tuple[int, int]:
    m = _FS_RE.search(text)
    if not m:
        raise ValueError("missing %FSLAX...% format spec")
    return int(m.group(1)), int(m.group(2))  # int_digits, frac_digits


def _decode(raw: int, frac: int) -> float:
    return raw / (10 ** frac)


def parse_edgecuts(gbr_path: Path) -> list[tuple[float, float]]:
    """Return ordered closed polygon as list of (x,y); first==last."""
    text = gbr_path.read_text()
    _, frac = _parse_format(text)

    segments: list[tuple[tuple[float, float], tuple[float, float]]] = []
    cur: tuple[float, float] | None = None

    for m in _COORD_RE.finditer(text):
        x = round(_decode(int(m.group(1)), frac), 4)
        y = round(_decode(int(m.group(2)), frac), 4)
        op = m.group(3)
        if op == "2":  # pen-up move
            cur = (x, y)
        elif op == "1":  # draw line
            if cur is None:
                raise ValueError("D01 before any D02")
            segments.append((cur, (x, y)))
            cur = (x, y)

    if not segments:
        raise ValueError("no segments parsed from gerber")

    # Build adjacency, then walk one closed loop.
    adj: dict[tuple[float, float], list[tuple[float, float]]] = defaultdict(list)
    for a, b in segments:
        adj[a].append(b)
        adj[b].append(a)

    start = segments[0][0]
    loop = [start]
    prev = None
    cur_pt = start
    while True:
        nbrs = [p for p in adj[cur_pt] if p != prev]
        if not nbrs:
            raise ValueError(f"dead-end at {cur_pt}")
        nxt = nbrs[0]
        loop.append(nxt)
        if nxt == start:
            break
        prev, cur_pt = cur_pt, nxt
        if len(loop) > len(segments) + 2:
            raise ValueError("loop walk exceeded segment count")

    return loop


# ---------- Excellon drill ----------

_TOOL_RE = re.compile(r"^T(\d+)C([\d.]+)")
_DRILL_COORD_RE = re.compile(r"^X(-?[\d.]+)Y(-?[\d.]+)")
_TOOL_SEL_RE = re.compile(r"^T(\d+)\s*$")


def parse_pth_holes(drl_path: Path, target_dia: float = 4.1) -> list[tuple[float, float]]:
    """Return list of (x,y) for the drill tool whose diameter matches target_dia."""
    target_tool: str | None = None
    tools: dict[str, float] = {}
    holes: list[tuple[float, float]] = []
    cur_tool: str | None = None

    for line in drl_path.read_text().splitlines():
        line = line.strip()
        m = _TOOL_RE.match(line)
        if m:
            tools[m.group(1)] = float(m.group(2))
            if abs(float(m.group(2)) - target_dia) < 0.01:
                target_tool = m.group(1)
            continue
        m = _TOOL_SEL_RE.match(line)
        if m:
            cur_tool = m.group(1)
            continue
        m = _DRILL_COORD_RE.match(line)
        if m and cur_tool == target_tool:
            holes.append((round(float(m.group(1)), 3), round(float(m.group(2)), 3)))

    if target_tool is None:
        raise ValueError(f"no tool with Ø{target_dia} found")
    return holes


@click.command()
@click.argument("gbr", type=click.Path(exists=True, path_type=Path))
@click.argument("drl", type=click.Path(exists=True, path_type=Path))
@click.option("--out", "out_dir", type=click.Path(path_type=Path),
              default=Path("data"), show_default=True)
def main(gbr: Path, drl: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    polygon = parse_edgecuts(gbr)
    holes = parse_pth_holes(drl, target_dia=4.1)

    (out_dir / "pcb_outline.json").write_text(json.dumps(polygon, indent=2))
    (out_dir / "mounting_holes.json").write_text(json.dumps(holes, indent=2))

    bbox = (min(p[0] for p in polygon), min(p[1] for p in polygon),
            max(p[0] for p in polygon), max(p[1] for p in polygon))
    click.echo(f"polygon: {len(polygon)} vertices, bbox={bbox}")
    click.echo(f"holes:   {len(holes)} @ Ø4.1mm")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test**

Run: `pytest tests/test_parse_gerber.py -v`
Expected: PASS. If bbox or hole assertion fails, inspect generated `data/pcb_outline.json` and reconcile against spec §2.1; the parser is correct only if bbox matches `(-8.5, -110.5, 135.0, 5.0)` to within 0.05mm.

- [ ] **Step 5: Generate canonical cached JSON in repo**

Run: `python scripts/parse_gerber.py data/raw/SofleKeyboard-EdgeCuts.gbr data/raw/SofleKeyboard-PTH.drl --out data/`
Expected: `data/pcb_outline.json` and `data/mounting_holes.json` written; stdout reports vertex count and bbox.

- [ ] **Step 6: Commit**

```bash
git add scripts/parse_gerber.py tests/test_parse_gerber.py data/pcb_outline.json data/mounting_holes.json
git commit -m "parse: GERBER edgecuts + Excellon drill → JSON cache"
```

---

## Task 5: CPL Parser

**Files:**
- Create: `scripts/parse_cpl.py`
- Create: `tests/test_parse_cpl.py`
- Generates: `data/components.json`

The CPL is the JLCPCB-style pick-and-place CSV with header `Designator,Mid X,Mid Y,Layer,Rotation` (or similar). We extract the components named in `constants.py`.

- [ ] **Step 1: Inspect header**

Run: `head -3 data/raw/CPL-SofleKeyboard.csv`
Expected: header line + 2 sample rows. Note exact column names; adjust parser if they differ from the assumed `Designator, Mid X, Mid Y, Layer, Rotation`.

- [ ] **Step 2: Write failing test `tests/test_parse_cpl.py`**

```python
"""Tests for CPL parser."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_parse_cpl_extracts_known_components(tmp_path):
    out_dir = tmp_path / "data"
    out_dir.mkdir()
    csv = ROOT / "data" / "raw" / "CPL-SofleKeyboard.csv"
    script = ROOT / "scripts" / "parse_cpl.py"
    subprocess.run(
        [sys.executable, str(script), str(csv), "--out", str(out_dir)],
        check=True,
    )
    data = json.loads((out_dir / "components.json").read_text())

    # Spec §2.3 expected positions (PCB coords, mm). Tolerances per CPL precision.
    expected = {
        "U1":   (10.27, -16.16),    # MCU
        "SW31": (2.945, -43.23),    # slide switch
        "RSW1": (7.72,  -45.35),    # reset
        "SW25": (9.47,  -65.95),    # rotary encoder
        "J3":   (5.22,  -33.69),    # OLED socket
    }
    for des, (ex, ey) in expected.items():
        assert des in data, f"missing {des}"
        x, y = data[des]["x"], data[des]["y"]
        assert abs(x - ex) < 0.05, f"{des} X: {x} vs {ex}"
        assert abs(y - ey) < 0.05, f"{des} Y: {y} vs {ey}"
```

- [ ] **Step 3: Run; verify fail**

Run: `pytest tests/test_parse_cpl.py -v`
Expected: FAIL — `scripts/parse_cpl.py` missing.

- [ ] **Step 4: Create `scripts/parse_cpl.py`**

```python
"""Parse JLCPCB CPL (pick-and-place) CSV → JSON keyed by designator."""
from __future__ import annotations
import csv
import json
from pathlib import Path
import click


def parse_cpl(csv_path: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    with csv_path.open() as f:
        reader = csv.DictReader(f)
        # Build a lower-cased fieldname map so we tolerate minor header variants.
        fmap = {k.strip().lower(): k for k in reader.fieldnames or []}

        def col(*names: str) -> str:
            for n in names:
                if n in fmap:
                    return fmap[n]
            raise KeyError(f"none of {names} present in {list(fmap)}")

        c_des = col("designator")
        c_x   = col("mid x", "midx", "x")
        c_y   = col("mid y", "midy", "y")
        c_lay = col("layer")
        c_rot = col("rotation")

        for row in reader:
            des = row[c_des].strip()
            try:
                out[des] = {
                    "x": float(row[c_x]),
                    "y": float(row[c_y]),
                    "layer": row[c_lay].strip().lower(),
                    "rotation": float(row[c_rot]),
                }
            except ValueError:
                continue  # skip malformed rows
    return out


@click.command()
@click.argument("csv_path", type=click.Path(exists=True, path_type=Path))
@click.option("--out", "out_dir", type=click.Path(path_type=Path),
              default=Path("data"), show_default=True)
def main(csv_path: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    data = parse_cpl(csv_path)
    (out_dir / "components.json").write_text(json.dumps(data, indent=2, sort_keys=True))
    click.echo(f"components: {len(data)}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run test**

Run: `pytest tests/test_parse_cpl.py -v`
Expected: PASS. If a designator is missing, the CPL may use a different name — open the CSV and reconcile spec §2.3.

- [ ] **Step 6: Generate canonical components.json**

Run: `python scripts/parse_cpl.py data/raw/CPL-SofleKeyboard.csv --out data/`
Expected: `data/components.json` written.

- [ ] **Step 7: Commit**

```bash
git add scripts/parse_cpl.py tests/test_parse_cpl.py data/components.json
git commit -m "parse: CPL CSV → components.json"
```

---

## Task 6: PCB Geometry Module (Load + Offset)

**Files:**
- Create: `src/sofle_case/pcb_geometry.py`
- Create: `tests/test_pcb_geometry.py`

Provides `load_pcb_polygon()` (from JSON, in PCB coords) and `polygon_in_case_coords()` (translated via `pcb_to_case`). Build123d `offset` (on a `Face`/`Sketch`) handles the +0.5mm cavity expansion at build time, so this module returns plain vertex lists; the build code converts them to a build123d sketch.

- [ ] **Step 1: Write failing test `tests/test_pcb_geometry.py`**

```python
"""Tests for PCB polygon loader."""
from sofle_case import constants as C
from sofle_case.pcb_geometry import load_pcb_polygon, polygon_in_case_coords


def test_load_polygon_closed():
    poly = load_pcb_polygon()
    assert len(poly) >= 6
    assert poly[0] == poly[-1]


def test_load_polygon_bbox():
    poly = load_pcb_polygon()
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    assert abs(min(xs) - C.PCB_X_MIN) < 0.05
    assert abs(max(xs) - C.PCB_X_MAX) < 0.05
    assert abs(min(ys) - C.PCB_Y_MIN) < 0.05
    assert abs(max(ys) - C.PCB_Y_MAX) < 0.05


def test_translate_to_case_coords():
    case_poly = polygon_in_case_coords()
    xs = [p[0] for p in case_poly]
    ys = [p[1] for p in case_poly]
    # PCB is centered in case, so polygon should sit fully inside (0..OUTER_*).
    assert min(xs) > 0
    assert max(xs) < C.OUTER_WIDTH
    assert min(ys) > 0
    assert max(ys) < C.OUTER_DEPTH
```

- [ ] **Step 2: Run; verify fail**

Run: `pytest tests/test_pcb_geometry.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Create `src/sofle_case/pcb_geometry.py`**

```python
"""Load cached PCB outline polygon and translate into case coords."""
from __future__ import annotations
import json
from pathlib import Path
from . import constants as C


_DATA = Path(__file__).resolve().parents[2] / "data"


def load_pcb_polygon() -> list[tuple[float, float]]:
    """Ordered closed polygon in PCB coords (first == last)."""
    raw = json.loads((_DATA / "pcb_outline.json").read_text())
    return [tuple(p) for p in raw]


def load_mounting_holes() -> list[tuple[float, float]]:
    raw = json.loads((_DATA / "mounting_holes.json").read_text())
    return [tuple(p) for p in raw]


def polygon_in_case_coords() -> list[tuple[float, float]]:
    return [C.pcb_to_case(x, y) for x, y in load_pcb_polygon()]


def holes_in_case_coords() -> list[tuple[float, float]]:
    return [C.pcb_to_case(x, y) for x, y in load_mounting_holes()]
```

- [ ] **Step 4: Run test**

Run: `pytest tests/test_pcb_geometry.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add src/sofle_case/pcb_geometry.py tests/test_pcb_geometry.py
git commit -m "geometry: load PCB polygon + translate to case coords"
```

---

## Task 7: Mounting Hole Verification Test

**Files:**
- Create: `tests/test_holes.py`

Cross-checks parsed holes against `constants.MOUNTING_HOLES` (the spec-derived values) — guards against drift between the cached JSON and the constants module.

- [ ] **Step 1: Write test `tests/test_holes.py`**

```python
"""Verify cached mounting-hole JSON matches constants.MOUNTING_HOLES."""
from sofle_case import constants as C
from sofle_case.pcb_geometry import load_mounting_holes


def test_holes_match_constants():
    parsed = {(round(x, 2), round(y, 2)) for x, y in load_mounting_holes()}
    expected = {(round(x, 2), round(y, 2)) for x, y in C.MOUNTING_HOLES}
    assert parsed == expected, f"drift: parsed={parsed} vs constants={expected}"


def test_five_holes():
    assert len(load_mounting_holes()) == 5
```

- [ ] **Step 2: Run**

Run: `pytest tests/test_holes.py -v`
Expected: 2 passed (already cached JSON aligns with spec values).

- [ ] **Step 3: Commit**

```bash
git add tests/test_holes.py
git commit -m "test: cached holes match constants"
```

---

## Task 8: Stepped Standoff Module

**Files:**
- Create: `src/sofle_case/standoffs.py`
- Create: `tests/test_standoff.py`

A standoff is `lower_cyl + upper_cyl - tap_bore` where:
- Lower cylinder: Z=2.0..4.5, OD=5.5
- Upper cylinder: Z=4.5..6.5, OD=3.5
- Tap bore: Z=6.5..2.5 (depth 4mm), Ø=1.6, drilled top-down

- [ ] **Step 1: Write failing test `tests/test_standoff.py`**

```python
"""Tests for stepped standoff geometry."""
from build123d import Part
from sofle_case import constants as C
from sofle_case.standoffs import stepped_standoff


def test_returns_part():
    s = stepped_standoff(at=(50.0, 50.0))
    assert isinstance(s, Part)


def test_height():
    s = stepped_standoff(at=(50.0, 50.0))
    bb = s.bounding_box()
    # Standoff goes from FLOOR_THICKNESS (2.0) up to PLATE_SEAT_Z (6.5)
    assert abs(bb.min.Z - C.FLOOR_THICKNESS) < 0.01
    assert abs(bb.max.Z - C.PLATE_SEAT_Z) < 0.01


def test_lower_diameter():
    """At Z just above floor, OD should be STANDOFF_OD_LOWER."""
    s = stepped_standoff(at=(0.0, 0.0))
    bb = s.bounding_box()
    # XY half-extent at the widest cross-section is OD_LOWER/2
    assert abs((bb.max.X - bb.min.X) - C.STANDOFF_OD_LOWER) < 0.01
    assert abs((bb.max.Y - bb.min.Y) - C.STANDOFF_OD_LOWER) < 0.01


def test_centered_at_xy():
    s = stepped_standoff(at=(12.34, 56.78))
    bb = s.bounding_box()
    cx = (bb.min.X + bb.max.X) / 2
    cy = (bb.min.Y + bb.max.Y) / 2
    assert abs(cx - 12.34) < 0.01
    assert abs(cy - 56.78) < 0.01
```

- [ ] **Step 2: Run; verify fail**

Run: `pytest tests/test_standoff.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Create `src/sofle_case/standoffs.py`**

```python
"""Stepped standoff: lower shoulder (PCB seat) + upper pin (through PCB) + M2 tap bore."""
from __future__ import annotations
from build123d import Part, Cylinder, Pos, Axis
from . import constants as C


def stepped_standoff(at: tuple[float, float]) -> Part:
    """Build one standoff in case coords. Origin = (at_x, at_y, 0)."""
    x, y = at

    lower_h = C.PCB_SEAT_Z - C.FLOOR_THICKNESS          # 2.5
    upper_h = C.PLATE_SEAT_Z - C.PCB_SEAT_Z             # 2.0
    lower_z = C.FLOOR_THICKNESS + lower_h / 2           # cylinder is centered → place at midpoint
    upper_z = C.PCB_SEAT_Z + upper_h / 2

    lower = Pos(x, y, lower_z) * Cylinder(
        radius=C.STANDOFF_OD_LOWER / 2, height=lower_h
    )
    upper = Pos(x, y, upper_z) * Cylinder(
        radius=C.STANDOFF_OD_UPPER / 2, height=upper_h
    )

    bore_top = C.PLATE_SEAT_Z
    bore_bot = C.PLATE_SEAT_Z - C.STANDOFF_TAP_DEPTH
    bore_z   = (bore_top + bore_bot) / 2
    bore = Pos(x, y, bore_z) * Cylinder(
        radius=C.STANDOFF_TAP_DIA / 2, height=C.STANDOFF_TAP_DEPTH
    )

    return (lower + upper) - bore
```

- [ ] **Step 4: Run test**

Run: `pytest tests/test_standoff.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/sofle_case/standoffs.py tests/test_standoff.py
git commit -m "standoff: stepped standoff with M2 self-tap bore"
```

---

## Task 9: Outer Tray (Shell + Inner Cavity + Top Chamfer)

**Files:**
- Create: `src/sofle_case/tray.py`
- Create: `tests/test_tray.py`

Outer rounded-rect extruded to `MAIN_RIM_Z`. Cavity = PCB polygon (in case coords) offset outward by `PCB_XY_CLEARANCE`, extruded from `FLOOR_THICKNESS` to `MAIN_RIM_Z + 0.01` (overshoot to prevent zero-thickness top), subtracted. Top chamfer on outer top edges only.

- [ ] **Step 1: Write failing test `tests/test_tray.py`**

```python
"""Tray (shell + cavity) tests."""
from build123d import Part
from sofle_case import constants as C
from sofle_case.tray import build_tray


def test_returns_part():
    t = build_tray()
    assert isinstance(t, Part)


def test_outer_bbox():
    t = build_tray()
    bb = t.bounding_box()
    assert abs((bb.max.X - bb.min.X) - C.OUTER_WIDTH) < 0.01
    assert abs((bb.max.Y - bb.min.Y) - C.OUTER_DEPTH) < 0.01
    assert abs(bb.min.Z - 0.0) < 0.01
    assert abs(bb.max.Z - C.MAIN_RIM_Z) < 0.01


def test_volume_smaller_than_solid_box():
    """Hollow tray < solid box of the same outer dims."""
    t = build_tray()
    solid_vol = C.OUTER_WIDTH * C.OUTER_DEPTH * C.MAIN_RIM_Z
    assert t.volume < solid_vol * 0.7
```

- [ ] **Step 2: Run; verify fail**

Run: `pytest tests/test_tray.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Create `src/sofle_case/tray.py`**

```python
"""Outer shell + inner cavity (PCB polygon offset by PCB_XY_CLEARANCE) + top chamfer."""
from __future__ import annotations
from build123d import (
    Part, Pos, RectangleRounded, Polyline, make_face, extrude, offset, Kind,
    Plane, BuildPart, BuildSketch, Locations,
)
from . import constants as C
from .pcb_geometry import polygon_in_case_coords


def _outer_shell() -> Part:
    """Solid rounded-rect prism in case coords; lower-left at (0,0,0)."""
    with BuildPart() as bp:
        with BuildSketch(Plane.XY.offset(0)):
            with Locations((C.OUTER_WIDTH / 2, C.OUTER_DEPTH / 2)):
                RectangleRounded(C.OUTER_WIDTH, C.OUTER_DEPTH, C.CORNER_RADIUS)
        extrude(amount=C.MAIN_RIM_Z)
    return bp.part


def _cavity_solid() -> Part:
    """PCB polygon offset by +PCB_XY_CLEARANCE, extruded from floor to over-rim."""
    poly = polygon_in_case_coords()
    # Drop closing duplicate for Polyline.
    pts = poly[:-1] if poly[0] == poly[-1] else poly

    with BuildPart() as bp:
        with BuildSketch(Plane.XY):
            face = make_face(Polyline(*pts, close=True))
            face = offset(face, amount=C.PCB_XY_CLEARANCE, kind=Kind.INTERSECTION)
        extrude(amount=C.MAIN_RIM_Z + 1.0)
    # Translate so the cavity starts at Z=FLOOR_THICKNESS (extrude went up from Z=0).
    return Pos(0, 0, C.FLOOR_THICKNESS) * bp.part


def _chamfer_top_edges(part: Part) -> Part:
    """Chamfer only the outer top edges (Z == MAIN_RIM_Z) by TOP_CHAMFER."""
    top_edges = part.edges().filter_by_position(
        axis="Z", minimum=C.MAIN_RIM_Z - 0.001, maximum=C.MAIN_RIM_Z + 0.001
    )
    if not top_edges:
        return part
    from build123d import chamfer
    return chamfer(top_edges, length=C.TOP_CHAMFER)


def build_tray() -> Part:
    shell = _outer_shell()
    cavity = _cavity_solid()
    hollow = shell - cavity
    return _chamfer_top_edges(hollow)
```

- [ ] **Step 4: Run test**

Run: `pytest tests/test_tray.py -v`
Expected: 3 passed. If the chamfer call breaks the model (build123d API drift), drop the chamfer call and ship without it; revisit later.

- [ ] **Step 5: Commit**

```bash
git add src/sofle_case/tray.py tests/test_tray.py
git commit -m "tray: outer shell + PCB-shaped cavity + top chamfer"
```

---

## Task 10: MCU Cover

**Files:**
- Create: `src/sofle_case/mcu_cover.py`
- Create: `tests/test_mcu_cover.py`

Adds a hollow box on top of the rim. Footprint: `MCU_COVER_W × MCU_COVER_D`, +Y face flush with case +Y outer wall, X centered on `MCU_POS.x`, Z range `MAIN_RIM_Z..MCU_COVER_Z`. Subtracts an inner cavity (wall thickness `WALL_THICKNESS`) so the interior continues all the way down to `PCB_TOP_Z`.

- [ ] **Step 1: Write failing test `tests/test_mcu_cover.py`**

```python
from build123d import Part
from sofle_case import constants as C
from sofle_case.mcu_cover import build_mcu_cover


def test_returns_part():
    p = build_mcu_cover()
    assert isinstance(p, Part)


def test_height_extends_above_rim():
    p = build_mcu_cover()
    bb = p.bounding_box()
    assert abs(bb.max.Z - C.MCU_COVER_Z) < 0.01
    # cover starts at PCB_TOP_Z (so the outer-wall merge handles below-rim region)
    assert bb.min.Z <= C.MAIN_RIM_Z


def test_plus_y_flush_with_outer_wall():
    p = build_mcu_cover()
    bb = p.bounding_box()
    assert abs(bb.max.Y - C.OUTER_DEPTH) < 0.01


def test_x_centered_on_mcu():
    p = build_mcu_cover()
    bb = p.bounding_box()
    cx = (bb.min.X + bb.max.X) / 2
    expected_cx = C.pcb_to_case(*C.MCU_POS)[0]
    assert abs(cx - expected_cx) < 0.01
```

- [ ] **Step 2: Run; verify fail**

Run: `pytest tests/test_mcu_cover.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Create `src/sofle_case/mcu_cover.py`**

```python
"""Raised MCU cover, merged with the +Y outer wall."""
from __future__ import annotations
from build123d import Part, Pos, Box, Align
from . import constants as C


def build_mcu_cover() -> Part:
    """Returns a Part to be UNION'd with the tray. The +Y face sits flush with the
    case +Y outer edge (y = OUTER_DEPTH). The bottom extends down to PCB_TOP_Z so
    that when union'd with the tray it merges seamlessly into the +Y wall."""
    mcu_x_case, _ = C.pcb_to_case(*C.MCU_POS)

    # Outer box
    z_low = C.PCB_TOP_Z
    z_high = C.MCU_COVER_Z
    h = z_high - z_low
    cx = mcu_x_case
    cy = C.OUTER_DEPTH - C.MCU_COVER_D / 2  # +Y face flush at OUTER_DEPTH

    outer = Pos(cx, cy, z_low + h / 2) * Box(
        C.MCU_COVER_W, C.MCU_COVER_D, h, align=(Align.CENTER, Align.CENTER, Align.CENTER)
    )

    # Inner cavity: shrink XY by WALL_THICKNESS on the three closed sides
    # (-X, +X, -Y); +Y is flush with the wall and shares thickness with the case wall,
    # so we leave that side full-thickness via positioning trick: shrink width fully,
    # then shift cavity -Y by WALL_THICKNESS/2 to keep +Y wall solid.
    inner_w = C.MCU_COVER_W - 2 * C.WALL_THICKNESS
    inner_d = C.MCU_COVER_D - 2 * C.WALL_THICKNESS
    inner_h = h + 0.02
    inner_cy = cy - C.WALL_THICKNESS / 2 + C.WALL_THICKNESS / 2  # net 0 — see note
    # Net: inner cavity is centered on the outer box; the +Y wall thickness is
    # already handled because the tray's +Y wall (Z<=MAIN_RIM_Z) overlaps and the
    # USB-C cutout in Task 11 will pierce the +Y wall over the full Z range.
    inner = Pos(cx, cy, z_low + inner_h / 2) * Box(
        inner_w, inner_d, inner_h, align=(Align.CENTER, Align.CENTER, Align.CENTER)
    )

    return outer - inner
```

- [ ] **Step 4: Run test**

Run: `pytest tests/test_mcu_cover.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/sofle_case/mcu_cover.py tests/test_mcu_cover.py
git commit -m "mcu_cover: raised hollow box flush with +Y wall"
```

---

## Task 11: Cutouts (USB-C, Slide Switch, Reset, Floor Recess)

**Files:**
- Create: `src/sofle_case/cutouts.py`
- Create: `tests/test_cutouts.py`

Each function returns a `Part` to be SUBTRACTED from the case. Boxes are sized larger than the wall so they fully pierce.

- [ ] **Step 1: Write failing test `tests/test_cutouts.py`**

```python
from build123d import Part
from sofle_case import constants as C
from sofle_case.cutouts import (
    usb_c_cutout, slide_switch_cutout, reset_pin_cutout, floor_recess,
)


def test_usb_c_returns_part():
    assert isinstance(usb_c_cutout(), Part)


def test_usb_c_at_plus_y_wall():
    bb = usb_c_cutout().bounding_box()
    # Cutout must straddle the +Y outer wall (y = OUTER_DEPTH)
    assert bb.min.Y < C.OUTER_DEPTH < bb.max.Y


def test_usb_c_z_centered():
    bb = usb_c_cutout().bounding_box()
    cz = (bb.min.Z + bb.max.Z) / 2
    assert abs(cz - C.USB_C_Z_CENTER) < 0.01


def test_slide_switch_at_minus_x_wall():
    bb = slide_switch_cutout().bounding_box()
    assert bb.min.X < 0 < bb.max.X


def test_reset_pin_diameter():
    bb = reset_pin_cutout().bounding_box()
    # Cylinder along X; cross-section in YZ plane is the pin diameter.
    assert abs((bb.max.Y - bb.min.Y) - C.RESET_PIN_DIA) < 0.01
    assert abs((bb.max.Z - bb.min.Z) - C.RESET_PIN_DIA) < 0.01


def test_floor_recess_dims():
    bb = floor_recess().bounding_box()
    assert abs((bb.max.X - bb.min.X) - C.SLIDE_SWITCH_RECESS_W) < 0.01
    assert abs((bb.max.Y - bb.min.Y) - C.SLIDE_SWITCH_RECESS_D) < 0.01
    assert abs((bb.max.Z - bb.min.Z) - C.SLIDE_SWITCH_RECESS_DEPTH) < 0.01
```

- [ ] **Step 2: Run; verify fail**

Run: `pytest tests/test_cutouts.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Create `src/sofle_case/cutouts.py`**

```python
"""Subtractive cutouts: USB-C (in MCU cover +Y face), slide-switch slot (-X wall),
reset pinhole (-X wall), floor recess for slide-switch body."""
from __future__ import annotations
from build123d import Part, Pos, Rot, Box, Cylinder, Align, Axis
from . import constants as C


_PIERCE = 6.0  # extra mm to ensure the cutout fully crosses any wall


def usb_c_cutout() -> Part:
    """Through-slot in +Y wall (within MCU cover) at MCU X, centered Z=USB_C_Z_CENTER."""
    cx, _ = C.pcb_to_case(*C.MCU_POS)
    cy = C.OUTER_DEPTH  # the +Y wall plane
    cz = C.USB_C_Z_CENTER
    return Pos(cx, cy, cz) * Box(
        C.USB_C_W, C.WALL_THICKNESS + _PIERCE, C.USB_C_H,
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
    )


def slide_switch_cutout() -> Part:
    """Through-slot in -X wall at slide-switch Y; Z range per spec."""
    _, cy = C.pcb_to_case(*C.SW_SLIDE_POS)
    z_lo, z_hi = C.SLIDE_SWITCH_Z_RANGE
    cz = (z_lo + z_hi) / 2
    return Pos(0.0, cy, cz) * Box(
        C.WALL_THICKNESS + _PIERCE, C.SLIDE_SWITCH_W, C.SLIDE_SWITCH_H,
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
    )


def reset_pin_cutout() -> Part:
    """Cylindrical pinhole in -X wall, axis along X."""
    _, cy = C.pcb_to_case(*C.SW_RESET_POS)
    cz = C.RESET_Z_CENTER
    cyl = Cylinder(
        radius=C.RESET_PIN_DIA / 2,
        height=C.WALL_THICKNESS + _PIERCE,
    )
    # Default cylinder axis is Z; rotate to X.
    return Pos(0.0, cy, cz) * Rot(0, 90, 0) * cyl


def floor_recess() -> Part:
    """Rectangular pocket in floor under slide switch body."""
    cx, cy = C.pcb_to_case(*C.SW_SLIDE_POS)
    cz = C.FLOOR_THICKNESS - C.SLIDE_SWITCH_RECESS_DEPTH / 2
    return Pos(cx, cy, cz) * Box(
        C.SLIDE_SWITCH_RECESS_W, C.SLIDE_SWITCH_RECESS_D, C.SLIDE_SWITCH_RECESS_DEPTH,
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
    )
```

- [ ] **Step 4: Run test**

Run: `pytest tests/test_cutouts.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/sofle_case/cutouts.py tests/test_cutouts.py
git commit -m "cutouts: USB-C, slide-switch slot, reset pin, floor recess"
```

---

## Task 12: Compose Case Half + Mirror

**Files:**
- Create: `src/sofle_case/case.py`
- Create: `tests/test_case.py`

- [ ] **Step 1: Write failing test `tests/test_case.py`**

```python
from typing import get_args
from build123d import Part
from sofle_case import constants as C
from sofle_case.case import build_case_half


def test_left_returns_part():
    p = build_case_half("left")
    assert isinstance(p, Part)


def test_left_outer_bbox():
    p = build_case_half("left")
    bb = p.bounding_box()
    assert abs((bb.max.X - bb.min.X) - C.OUTER_WIDTH) < 0.01
    assert abs((bb.max.Y - bb.min.Y) - C.OUTER_DEPTH) < 0.01
    assert abs(bb.min.Z - 0.0) < 0.01
    assert abs(bb.max.Z - C.MCU_COVER_Z) < 0.01


def test_right_is_mirror_of_left():
    left = build_case_half("left")
    right = build_case_half("right")
    # Volumes equal within float tolerance
    assert abs(left.volume - right.volume) / left.volume < 1e-3


def test_invalid_side_raises():
    import pytest as _pt
    with _pt.raises(ValueError):
        build_case_half("middle")
```

- [ ] **Step 2: Run; verify fail**

Run: `pytest tests/test_case.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Create `src/sofle_case/case.py`**

```python
"""Compose the full case half from tray + standoffs + MCU cover, minus cutouts."""
from __future__ import annotations
from typing import Literal
from build123d import Part, mirror, Plane
from . import constants as C
from .tray import build_tray
from .standoffs import stepped_standoff
from .mcu_cover import build_mcu_cover
from .cutouts import (
    usb_c_cutout, slide_switch_cutout, reset_pin_cutout, floor_recess,
)


Side = Literal["left", "right"]


def build_case_half(side: Side) -> Part:
    if side not in ("left", "right"):
        raise ValueError(f"side must be 'left' or 'right', got {side!r}")

    shell = build_tray()

    # 5 standoffs at PCB-coord mounting holes, translated to case coords.
    for hx, hy in C.MOUNTING_HOLES:
        cx, cy = C.pcb_to_case(hx, hy)
        shell += stepped_standoff(at=(cx, cy))

    # MCU cover (union)
    shell += build_mcu_cover()

    # Cutouts (subtract)
    shell -= usb_c_cutout()
    shell -= slide_switch_cutout()
    shell -= reset_pin_cutout()
    shell -= floor_recess()

    if side == "right":
        # Mirror about YZ plane that passes through case center X = OUTER_WIDTH/2
        # Build123d's mirror() goes through origin, so translate, mirror, translate back.
        from build123d import Pos
        shell = Pos(-C.OUTER_WIDTH / 2, 0, 0) * shell
        shell = mirror(shell, about=Plane.YZ)
        shell = Pos(C.OUTER_WIDTH / 2, 0, 0) * shell

    return shell
```

- [ ] **Step 4: Run test**

Run: `pytest tests/test_case.py -v`
Expected: 4 passed. (build_case_half is the slowest test — expect a few seconds per call.)

- [ ] **Step 5: Commit**

```bash
git add src/sofle_case/case.py tests/test_case.py
git commit -m "case: compose tray+standoffs+cover-cutouts; mirror for right half"
```

---

## Task 13: CLI Build Script (STL + STEP Export)

**Files:**
- Create: `scripts/build.py`
- Create: `tests/test_build_cli.py`

- [ ] **Step 1: Write failing test `tests/test_build_cli.py`**

```python
"""Smoke test the build CLI; verify STL + STEP files are written."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_left_writes_outputs(tmp_path):
    out = tmp_path / "output"
    out.mkdir()
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build.py"),
         "left", "--out", str(out)],
        check=True, cwd=str(ROOT),
    )
    stl = out / "sofle_case_left.stl"
    step = out / "sofle_case_left.step"
    assert stl.exists() and stl.stat().st_size > 1000
    assert step.exists() and step.stat().st_size > 1000
```

- [ ] **Step 2: Run; verify fail**

Run: `pytest tests/test_build_cli.py -v`
Expected: FAIL — `scripts/build.py` missing.

- [ ] **Step 3: Create `scripts/build.py`**

```python
"""CLI: build a Sofle case half and export STL + STEP.

Usage:
    python scripts/build.py left
    python scripts/build.py right --out output/
"""
from __future__ import annotations
from pathlib import Path
import click
from build123d import export_stl, export_step
from sofle_case.case import build_case_half


@click.command()
@click.argument("side", type=click.Choice(["left", "right"]))
@click.option("--out", "out_dir", type=click.Path(path_type=Path),
              default=Path("output"), show_default=True)
def main(side: str, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    click.echo(f"building {side} half…")
    part = build_case_half(side)  # type: ignore[arg-type]

    stl_path = out_dir / f"sofle_case_{side}.stl"
    step_path = out_dir / f"sofle_case_{side}.step"
    export_stl(part, str(stl_path))
    export_step(part, str(step_path))

    click.echo(f"  wrote {stl_path} ({stl_path.stat().st_size} bytes)")
    click.echo(f"  wrote {step_path} ({step_path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test**

Run: `pytest tests/test_build_cli.py -v`
Expected: PASS.

- [ ] **Step 5: Generate canonical artifacts**

Run: `python scripts/build.py left && python scripts/build.py right`
Expected: `output/sofle_case_left.{stl,step}` and `output/sofle_case_right.{stl,step}` written. Files are gitignored.

- [ ] **Step 6: Commit**

```bash
git add scripts/build.py tests/test_build_cli.py
git commit -m "cli: build.py exports STL + STEP per side"
```

---

## Task 14: Component-Clearance Test

**Files:**
- Create: `tests/test_clearances.py`

Asserts each cutout center is positioned where the corresponding component lives, and that the cutout extents clear the body by ≥ 0.3mm. (We don't have full component bodies modeled; we approximate with the spec dimensions.)

- [ ] **Step 1: Write `tests/test_clearances.py`**

```python
"""Each cutout aligns with its component; clearance ≥ 0.3 mm."""
from sofle_case import constants as C
from sofle_case.cutouts import (
    usb_c_cutout, slide_switch_cutout, reset_pin_cutout,
)


def _bb_center(part):
    bb = part.bounding_box()
    return (bb.min.X + bb.max.X) / 2, (bb.min.Y + bb.max.Y) / 2, (bb.min.Z + bb.max.Z) / 2


def test_usb_c_aligns_with_mcu_x():
    cx, _, _ = _bb_center(usb_c_cutout())
    expected, _ = C.pcb_to_case(*C.MCU_POS)
    assert abs(cx - expected) < 0.01


def test_slide_switch_aligns_with_sw31_y():
    _, cy, _ = _bb_center(slide_switch_cutout())
    _, expected = C.pcb_to_case(*C.SW_SLIDE_POS)
    assert abs(cy - expected) < 0.01


def test_reset_aligns_with_rsw1_y():
    _, cy, cz = _bb_center(reset_pin_cutout())
    _, expected = C.pcb_to_case(*C.SW_RESET_POS)
    assert abs(cy - expected) < 0.01
    assert abs(cz - C.RESET_Z_CENTER) < 0.01


def test_usb_c_clearance_above_pcb_top():
    """USB-C bottom must clear PCB top by ≥ 0.3 mm (port sits on MCU, MCU sits on PCB)."""
    bb = usb_c_cutout().bounding_box()
    assert bb.min.Z >= C.PCB_TOP_Z + 0.3
```

- [ ] **Step 2: Run**

Run: `pytest tests/test_clearances.py -v`
Expected: 4 passed.

- [ ] **Step 3: Commit**

```bash
git add tests/test_clearances.py
git commit -m "test: cutout-component clearance"
```

---

## Task 15: Print-Envelope Test

**Files:**
- Create: `tests/test_print_envelope.py`

- [ ] **Step 1: Write test**

```python
"""Each half must fit a 250×210mm FDM bed."""
from sofle_case.case import build_case_half

BED_X = 250.0
BED_Y = 210.0


def test_left_fits_bed():
    bb = build_case_half("left").bounding_box()
    assert (bb.max.X - bb.min.X) <= BED_X
    assert (bb.max.Y - bb.min.Y) <= BED_Y


def test_right_fits_bed():
    bb = build_case_half("right").bounding_box()
    assert (bb.max.X - bb.min.X) <= BED_X
    assert (bb.max.Y - bb.min.Y) <= BED_Y
```

- [ ] **Step 2: Run**

Run: `pytest tests/test_print_envelope.py -v`
Expected: 2 passed (162×131 well under 250×210).

- [ ] **Step 3: Commit**

```bash
git add tests/test_print_envelope.py
git commit -m "test: print envelope fits 250x210 bed"
```

---

## Task 16: Manifold-Validity Spot Check

**Files:**
- Create: `tests/test_manifold.py`

Build123d Parts are derived from OCCT solids that are manifold by construction *if* every union/subtract succeeded. We verify by checking `is_valid()` (build123d delegates to `BRepCheck_Analyzer`).

- [ ] **Step 1: Write test**

```python
from sofle_case.case import build_case_half


def test_left_is_valid():
    p = build_case_half("left")
    assert p.is_valid(), "left half failed BRepCheck"


def test_right_is_valid():
    p = build_case_half("right")
    assert p.is_valid(), "right half failed BRepCheck"
```

- [ ] **Step 2: Run**

Run: `pytest tests/test_manifold.py -v`
Expected: 2 passed.

If either fails, the most likely cause is an over-aggressive chamfer or a degenerate cavity edge from the offset; remove the chamfer (`tray.py::_chamfer_top_edges`) as the first debugging step.

- [ ] **Step 3: Commit**

```bash
git add tests/test_manifold.py
git commit -m "test: BRepCheck on both halves"
```

---

## Task 17: Final Acceptance Run + README Update

**Files:**
- Modify: `README.md` (add results section if not present)

- [ ] **Step 1: Run full suite**

Run: `pytest -v`
Expected: All tests passing (≥ 30 tests across the modules).

- [ ] **Step 2: Re-run canonical builds**

Run: `python scripts/build.py left && python scripts/build.py right`
Expected: Both STL+STEP regenerate without warnings; report file sizes.

- [ ] **Step 3: Visual sanity (manual, agent annotates result)**

Open both STLs in MeshLab or any STL viewer; confirm:
- 5 standoffs visible inside the tray
- MCU cover raised at +Y top-left (left half) / top-right (right half)
- USB-C slot visible on +Y face inside MCU cover
- Slide-switch slot + reset pinhole visible on -X face (left) / +X face (right)
- Floor recess visible from below
- PCB cavity matches expected irregular outline

If anything is wrong, file an issue against `constants.py` and re-run from Task 12.

- [ ] **Step 4: Append results to README**

Add to `README.md` under a new `## Status` heading: a list of what's verified working (test count, file sizes, last build date).

- [ ] **Step 5: Final commit**

```bash
git add README.md
git commit -m "docs: status section with first-build results"
```

---

## Self-Review Checklist (executed at plan-write time)

**Spec coverage:**
- §1 Goals → Tasks 9 (tray, open top), 10 (MCU cover), 11 (cutouts) ✅
- §2.1 PCB outline → Task 4 (parser), Task 6 (load) ✅
- §2.2 Mounting holes → Task 4 (parser), Task 7 (verify) ✅
- §2.3 Components → Task 5 (CPL parser); positions hardcoded in `constants.py` (canonical source) ✅
- §2.4 Heights → Task 2 (`constants.py` Z stack) ✅
- §3.1 Outer envelope → Task 9 ✅
- §3.2 Vertical stack → Task 2 (constants), enforced in test_constants.py ✅
- §3.3 Standoffs → Task 8 ✅
- §3.4 Inner cavity (no perimeter ledge default) → Task 9; `PCB_LEDGE_ENABLED` constant present ✅
- §3.5 MCU cover → Task 10 ✅
- §3.6 Wall cutouts → Task 11 ✅
- §3.7 Floor recess → Task 11 ✅
- §3.8 Bottom feet → no geometry needed (out of code scope) ✅
- §4 Right half mirror → Task 12 ✅
- §5.1 Project layout → Task 1 ✅
- §5.2 constants.py → Task 2 ✅
- §5.3 Build sequence → Task 12 ✅
- §5.4 GERBER parsing → Task 4 ✅
- §5.5 Tests → Tasks 2, 4, 5, 7, 8, 9, 10, 11, 12, 14, 15, 16 ✅
- §8 Acceptance criteria → Task 17 ✅

**Optional perimeter ledge (§3.4):** `PCB_LEDGE_ENABLED` is defined but not yet wired into `tray.py`. If/when needed, add a step under Task 9 that conditionally adds a ledge ring; deferred per YAGNI (default = False).

**Placeholders:** None (all "TODO"s removed; every code step has full code).

**Type/name consistency:** `build_case_half`, `build_tray`, `build_mcu_cover`, `stepped_standoff`, cutout names, `pcb_to_case`, `polygon_in_case_coords` — used identically in defining task and consumer task.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-25-sofle-v2-wireless-case-design.md`. Two execution options:

**1. Subagent-Driven (recommended)** — fresh subagent per task, review between tasks, fast iteration. REQUIRED SUB-SKILL: `superpowers:subagent-driven-development`.

**2. Inline Execution** — run tasks here using `superpowers:executing-plans`, batch with checkpoints.

Which approach?
