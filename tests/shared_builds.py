"""Session-cached wrappers for the expensive OCC builds.

Every ``build_*`` call drives the OpenCASCADE kernel and allocates C++ memory
that Python's GC does not track well; rebuilding per test made peak RSS grow
with suite size (~750 MB at ~230 tests, minutes of wall time). Importing
through this module builds each distinct part ONCE per test process and shares
the instance: tests treat parts as read-only (every probe is a boolean op that
returns a new object), so sharing does not change any test outcome.

Rule: in tests, import builders from here — never directly from sofle_case.*.
Uncached exceptions (e.g. ``build_case_half("middle")``) re-raise identically,
so negative tests are unaffected.
"""
from functools import cache

from sofle_case.case import build_case_half as _build_case_half
from sofle_case.tray import build_tray as _build_tray

build_case_half = cache(_build_case_half)
build_tray = cache(_build_tray)
