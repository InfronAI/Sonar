# Round invoice lines and tax

Each entry in `lines` has an integer `quantity` and a base-10 string `unit_price` expressed in currency units. Multiply each line by its quantity, convert to cents, and round each line to an integer with halves away from zero. Sum these rounded lines for `net_cents`. Compute tax once on that sum using integer `tax_bps` (10,000 basis points = 100%) with the same rounding rule. Return `net_cents`, `tax_cents`, and `total_cents` as integers. Negative amounts are possible.

Create `/app/solve.py`. It will be run with Python 3 and one JSON value on stdin. Print one JSON value to stdout. A worked example is available in `/app/example.json`. The verifier also uses other inputs.
