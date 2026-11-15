# Phase 3 · Task 9 — Property-based tests of the replay plume-grid codec

**Skills:** `plan-execution`, `testing-strategy`, `superpowers:test-driven-development`, `project-documentation`.

**Why:** the replay files and the 3D plume shader depend on `encode_log_u8` / `decode_log_u8`
(Task 7). Example tests check a few cells; these tests check the codec's laws for every input:
round trip within half a log step, monotonic coding, clamping and the byte count. Scenario and
variant determinism are already covered by Tasks 4 and 6.

**Verified by the planner (2026-11-13):** the file passes (4 tests) against a reference written
from the Task 7 interface and is clean under the project's ruff rules. A failure means the codec
deviates from Task 7 — fix the code, never the test.

## Files
| Action | Path |
|---|---|
| Create | `app/backend/tests/engineering/test_plume_field_properties.py` (full code below, verbatim) |

## Test (full code)
```python
"""Property-based tests of the log-scaled 8-bit plume grid codec (replay format).

The codec maps 0.1–1000 ppm onto codes 1–255 on a log scale (4 decades / 254 steps), code 0 for
below 0.1 ppm. Laws: a round trip stays within half a step (a factor of 10^(2/254) ≈ 1.0183),
the coding is monotonic, out-of-range values clamp, and the byte count equals the cell count.
"""

import math

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st

from plumetrace.engineering.plume_field import DECADES, PPM_MIN, decode_log_u8, encode_log_u8

LAW = settings(max_examples=300, derandomize=True, deadline=None, database=None)
HALF_STEP_DECADES = DECADES / 254 / 2
in_range = st.floats(PPM_MIN, PPM_MIN * 10**DECADES)


@LAW
@given(st.lists(in_range, min_size=1, max_size=64))
def test_round_trip_within_half_a_step(values: list[float]) -> None:
    """decode(encode(x)) differs from x by at most half a log step."""
    ppm = np.array(values)
    back = decode_log_u8(encode_log_u8(ppm), 1, len(values))[0]
    for x, y in zip(values, back, strict=True):
        assert abs(math.log10(y / x)) <= HALF_STEP_DECADES + 1e-12


@LAW
@given(st.floats(0.0, 1e6), st.floats(0.0, 1e6))
def test_coding_is_monotonic(a: float, b: float) -> None:
    """A larger concentration never gets a smaller code."""
    lo, hi = sorted((a, b))
    codes = encode_log_u8(np.array([lo, hi]))
    assert codes[0] <= codes[1]


@LAW
@given(st.floats(0.0, PPM_MIN, exclude_max=True), st.floats(PPM_MIN * 10**DECADES, 1e9))
def test_out_of_range_values_clamp(below: float, above: float) -> None:
    """Below 0.1 ppm → code 0 → 0.0; above 1000 ppm → code 255 → 1000 ppm."""
    codes = encode_log_u8(np.array([below, above]))
    assert list(codes) == [0, 255]
    back = decode_log_u8(codes, 1, 2)[0]
    assert back[0] == 0.0 and math.isclose(back[1], PPM_MIN * 10**DECADES, rel_tol=1e-12)


@LAW
@given(st.integers(1, 20), st.integers(1, 20), st.data())
def test_byte_count_matches_the_grid(ny: int, nx: int, data: st.DataObject) -> None:
    """One byte per cell, row-major, and decode restores the grid shape."""
    grid = np.array(data.draw(st.lists(st.floats(0.0, 2000.0), min_size=ny * nx, max_size=ny * nx)))
    encoded = encode_log_u8(grid.reshape(ny, nx))
    assert len(encoded) == ny * nx
    assert decode_log_u8(encoded, ny, nx).shape == (ny, nx)
```

## Steps
- [x] Copy → `cd app && uv run pytest backend/tests/engineering/test_plume_field_properties.py -q` → `4 passed`.
- [x] `python scripts/ci_local.py` green.
- [ ] **Docs.** REPLAY.md → "Plume grid encoding": add the four laws; `docs/reference/TESTING.md` → property-tests row. Work-log; `STATUS.md`: "Phase 3 complete — waiting for Gate 3 (scenario scripts)".
- [ ] **Commit** `test(replay): add property tests for the plume grid codec`.
