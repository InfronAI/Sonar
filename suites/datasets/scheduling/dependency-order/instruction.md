# Order dependent jobs

`jobs` lists distinct names. Each `[before,after]` in `edges` requires `before` to finish first. Duplicate edges represent the same requirement. Return the lexicographically smallest valid topological order across all jobs, including isolated jobs. Return JSON null if a cycle prevents completion. Edge endpoints always appear in `jobs`.

Create `/app/solve.py`. It will be run with Python 3 and one JSON value on stdin. Print one JSON value to stdout. A worked example is available in `/app/example.json`. The verifier also uses other inputs.
