# Integrate a calibrated force trace

Measurements [position_mm,force_mN] describe a piecewise-linear force along a track. Ignore acquisition order and use the last sample for any repeated position. Sort by position. Return the signed work along increasing position as `twice_microjoules`, the sum over adjacent pairs of (left_force+right_force)*distance_mm, and the `span_mm` from first to last sample. Fewer than two distinct positions give both values zero.

Create `/app/solve.py`. Read one JSON value from stdin and print one JSON value to stdout. See `/app/example.json` for a worked example.
