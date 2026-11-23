import json
import sys


from collections import defaultdict


def solve(rows):
    sites = defaultdict(lambda: {"before": {}, "after": {}})
    for plot, season, point, covered in rows:
        sites[plot][season][point] = covered
    out = {}
    for plot, seasons in sites.items():
        before, after = seasons["before"], seasons["after"]
        matched = before.keys() & after.keys()
        out[plot] = [len(matched), sum(after[p] - before[p] for p in matched)]
    return out


print(json.dumps(solve(json.load(sys.stdin)), allow_nan=False))
