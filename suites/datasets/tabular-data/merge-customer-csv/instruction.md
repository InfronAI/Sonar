# Merge customer revisions from CSV

The input is an object with a `csv` string. Its header is `id,revision,name,email`. Read quoted CSV fields correctly. For each ID keep the row with the highest integer revision, choosing the last row on a tie. Trim the chosen name and email, lowercase the email, and emit a list of `[id, name, email]` ordered by ID. IDs are strings and must keep leading zeros.

Create `/app/solve.py`. It will be run with Python 3 and one JSON value on stdin. Print one JSON value to stdout. A worked example is available in `/app/example.json`. The verifier also uses other inputs.
