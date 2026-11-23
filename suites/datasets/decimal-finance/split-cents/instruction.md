# Apportion cents by largest remainder

`total_cents` is a nonnegative integer. `weights` maps unique names to nonnegative integer weights with a positive sum. Allocate the floor of each exact proportional share. Give the leftover cents one per recipient in descending order of fractional remainder, breaking ties by ascending name. Return every name and its allocated integer cents, including zero allocations. Use exact arithmetic even for totals above 2^53.

Create `/app/solve.py`. It will be run with Python 3 and one JSON value on stdin. Print one JSON value to stdout. A worked example is available in `/app/example.json`. The verifier also uses other inputs.
