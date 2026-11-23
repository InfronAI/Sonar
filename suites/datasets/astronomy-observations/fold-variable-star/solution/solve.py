import json
import sys


from fractions import Fraction


def solve(data):
    bins = [[0, 0] for _ in range(data["bin_count"])]
    for t, flux in data["observations"]:
        if flux is None:
            continue
        phase = (t - data["epoch"]) % data["period"]
        cell = bins[phase * len(bins) // data["period"]]
        cell[0] += 1
        cell[1] += flux
    return [[n, str(Fraction(total, n)) if n else None] for n, total in bins]


print(json.dumps(solve(json.load(sys.stdin)), allow_nan=False))
