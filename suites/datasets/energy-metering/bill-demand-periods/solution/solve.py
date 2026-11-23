import json
import sys


def solve(data):
    out = []
    for lo, hi, rate in data["tariffs"]:
        energy = sum(max(0, min(hi, b) - max(lo, a)) * w for a, b, w in data["usage"])
        out.append([energy, energy * rate])
    return out


print(json.dumps(solve(json.load(sys.stdin)), allow_nan=False))
