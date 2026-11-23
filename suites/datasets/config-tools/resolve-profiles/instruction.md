# Resolve a named configuration profile

`profiles` maps names to objects with `values` and an optional `parent`. Follow the chain from `target`, then shallow-merge values from the oldest ancestor to the target. Object-valued settings replace the complete earlier setting. Ignore unrelated profiles. Return `{"values":...}` on success, `{"error":"missing"}` for an unknown target or parent, or `{"error":"cycle"}` for a repeated name in this chain.

Create `/app/solve.py`. It will be run with Python 3 and one JSON value on stdin. Print one JSON value to stdout. A worked example is available in `/app/example.json`. The verifier also uses other inputs.
