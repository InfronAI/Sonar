import json
import sys


def solve(data):
    out = []
    for ident, x, y in data["points"]:
        candidates = [
            ((e - w) * (n - s), zone)
            for zone, w, s, e, n in data["zones"]
            if w <= x < e and s <= y < n
        ]
        out.append([ident, min(candidates)[1] if candidates else None])
    return out


print(json.dumps(solve(json.load(sys.stdin)), allow_nan=False))
