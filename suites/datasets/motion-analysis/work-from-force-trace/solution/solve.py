import json
import sys


def solve(samples):
    ordered = sorted(dict(samples).items())
    work = sum((b[0] - a[0]) * (a[1] + b[1]) for a, b in zip(ordered, ordered[1:]))
    return {
        "twice_microjoules": work,
        "span_mm": ordered[-1][0] - ordered[0][0] if ordered else 0,
    }


print(json.dumps(solve(json.load(sys.stdin)), allow_nan=False))
