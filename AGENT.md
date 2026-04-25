# Agent Handoff

All dimensions live in `src/sofle_case/constants.py`. Change there; rebuild with `python scripts/build.py {left,right}`. Run `pytest` after every change.

PCB-derived data is cached as JSON in `data/`. Re-run `scripts/parse_gerber.py` only if the PCB sources change.

Build sequence: see `src/sofle_case/case.py::build_case_half`.
