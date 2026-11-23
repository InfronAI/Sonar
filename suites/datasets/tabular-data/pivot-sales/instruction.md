# Build a sales pivot

Input contains `sales`, a list of `[store, sku, units]`. Units are signed integers. Sum them per store and SKU. Emit an object mapping each store to its nonzero SKU totals. Omit stores with no remaining entries. Store and SKU identifiers are case-sensitive.

Create `/app/solve.py`. It will be run with Python 3 and one JSON value on stdin. Print one JSON value to stdout. A worked example is available in `/app/example.json`. The verifier also uses other inputs.
