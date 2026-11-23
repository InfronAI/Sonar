import json
import sys
from string import Formatter

def names(template):
    return {field for _, field, _, _ in Formatter().parse(template) if field is not None}

data = json.load(sys.stdin)
rows = []
for key, template in sorted(data["source"].items()):
    expected = names(template)
    actual = names(data["translated"].get(key, ""))
    if expected != actual:
        rows.append([key, sorted(expected - actual), sorted(actual - expected)])
print(json.dumps(rows))
