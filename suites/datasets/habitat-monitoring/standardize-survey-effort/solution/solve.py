import json
import sys


from collections import defaultdict
from fractions import Fraction


def solve(rows):
    by_site = defaultdict(lambda: [0, 0])
    for site, minutes, birds, valid in rows:
        totals = by_site[site]
        if valid and minutes > 0:
            totals[0] += minutes
            totals[1] += birds
    return {s: str(Fraction(60 * n, t)) if t else None for s, (t, n) in by_site.items()}


print(json.dumps(solve(json.load(sys.stdin)), allow_nan=False))
