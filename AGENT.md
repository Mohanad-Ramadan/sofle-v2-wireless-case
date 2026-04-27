# Agent Handoff

All dimensions live in `src/sofle_case/constants.py`. Change there; rebuild with `python scripts/build.py {left,right}`. Run `pytest` after every change.

PCB-derived data is cached as JSON in `data/`. Re-run `scripts/parse_gerber.py` only if the PCB sources change.

Build sequence: see `src/sofle_case/case.py::build_case_half`.

## OCP CAD Viewer

Every geometry module (`case.py`, `tray.py`, `standoffs.py`, `mcu_cover.py`, `cutouts.py`) has an `if __name__ == "__main__":` block that calls `show()`. Run any module directly to preview it:

```bash
source .venv/bin/activate
python src/sofle_case/case.py       # shows left + right halves
python src/sofle_case/tray.py       # shows tray shell
python src/sofle_case/standoffs.py  # shows one standoff
python src/sofle_case/mcu_cover.py  # shows MCU cover
python src/sofle_case/cutouts.py    # shows all 4 cutouts labelled
python scripts/build.py left --show # builds + exports + opens viewer
```

**Rule for new files:** any module that produces a `Part` or `Assembly` must include:

```python
if __name__ == "__main__":
    from ocp_vscode import show
    show(<the_part_or_assembly>, name="<descriptive_name>")
```

Keep the import inside the block so `ocp_vscode` remains an optional dev dependency and never breaks production imports.
