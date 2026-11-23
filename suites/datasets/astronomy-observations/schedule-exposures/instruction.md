# Find complete telescope exposure windows

Available observing windows [start,end] use integer minutes and half-open bounds. Merge overlapping or adjacent windows. Remove all blocked intervals (also half-open; overlaps possible). Within each resulting free interval place as many full exposures of positive length as possible, starting at the left edge. A nonnegative readout gap is required between successive exposures in the same free interval; no gap after its last exposure. Return ordered exposure start times.

Create `/app/solve.py`. Read one JSON value from stdin and print one JSON value to stdout. See `/app/example.json` for a worked example.
