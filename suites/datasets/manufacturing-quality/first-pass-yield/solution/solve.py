import json
import sys


from collections import defaultdict


def solve(rows):
    units = defaultdict(list)
    for line, unit, time, seq, passed in rows:
        units[line, unit].append((time, seq, passed))
    result = defaultdict(lambda: [0, 0, 0])
    for (line, _), checks in units.items():
        totals = result[line]
        totals[0] += 1
        totals[1] += min(checks)[2]
        totals[2] += any(p for _, _, p in checks)
    return dict(result)


print(json.dumps(solve(json.load(sys.stdin)), allow_nan=False))
