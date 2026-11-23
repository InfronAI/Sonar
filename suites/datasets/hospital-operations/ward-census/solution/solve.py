import json
import sys


from collections import defaultdict


def solve(data):
    lo, hi = data["window"]
    beds = defaultdict(list)
    result = {}
    for ward, bed, start, end in data["stays"]:
        result[ward] = 0
        left, right = max(lo, start), min(hi, hi if end is None else end)
        if left < right:
            beds[ward, bed].append((left, right))
    for (ward, _), spans in beds.items():
        covered = lo
        for left, right in sorted(spans):
            result[ward] += max(0, right - max(covered, left))
            covered = max(covered, right)
    return result


print(json.dumps(solve(json.load(sys.stdin)), allow_nan=False))
