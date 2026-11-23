import csv
import io
import json
import sys

latest = {}
for row in csv.DictReader(io.StringIO(json.load(sys.stdin)["csv"])):
    key = row["id"]
    revision = int(row["revision"])
    if key not in latest or revision >= latest[key][0]:
        latest[key] = (revision, row["name"].strip(), row["email"].strip().lower())

print(json.dumps([[key, *latest[key][1:]] for key in sorted(latest)]))
