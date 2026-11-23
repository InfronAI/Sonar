# Audit translation placeholders

Input `source` and `translated` map string IDs to Python format strings. Fields are simple named identifiers with optional plain format specifications. Doubled braces are literal; repeat occurrences count once. Audit all source IDs. A missing translation has no placeholders. Ignore translation-only IDs. For every ID with a mismatch, emit `[id, missing_names, extra_names]`, sorted by ID and with each name list sorted.

Create `/app/solve.py`. It will be run with Python 3 and one JSON value on stdin. Print one JSON value to stdout. A worked example is available in `/app/example.json`. The verifier also uses other inputs.
