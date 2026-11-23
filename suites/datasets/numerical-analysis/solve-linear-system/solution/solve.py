import json
import sys


from fractions import Fraction


def solve(rows):
    a = [[Fraction(x) for x in r] for r in rows]
    n = len(a[0]) - 1
    pivots = []
    for col in range(n):
        i = len(pivots)
        j = next((j for j in range(i, len(a)) if a[j][col]), None)
        if j is None:
            continue
        a[i], a[j] = a[j], a[i]
        a[i] = [x / a[i][col] for x in a[i]]
        for j, r in enumerate(a):
            if j != i and r[col]:
                a[j] = [x - r[col] * y for x, y in zip(r, a[i])]
        pivots.append(col)
    if any(not any(r[:-1]) and r[-1] for r in a):
        return {"status": "inconsistent"}
    if len(pivots) < n:
        return {"status": "underdetermined"}
    return {"status": "unique", "values": [str(a[i][-1]) for i in range(n)]}


print(json.dumps(solve(json.load(sys.stdin)), allow_nan=False))
