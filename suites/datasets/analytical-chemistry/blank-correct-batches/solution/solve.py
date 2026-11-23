import json
import sys


from collections import defaultdict
from fractions import Fraction


def solve(rows):
    blanks = defaultdict(list)
    for batch, _, kind, x in rows:
        if kind == "blank":
            blanks[batch].append(x)
    median = {}
    for batch, values in blanks.items():
        values.sort()
        n = len(values)
        median[batch] = Fraction(values[(n - 1) // 2] + values[n // 2], 2)
    return [
        [i, str(x - median[b]) if b in median else None]
        for b, i, k, x in rows
        if k == "sample"
    ]


print(json.dumps(solve(json.load(sys.stdin)), allow_nan=False))
