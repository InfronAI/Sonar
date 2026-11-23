import json
import sys


from collections import defaultdict
from fractions import Fraction


def solve(data):
    normals = {(s, m): v for s, m, v in data["normals"]}
    groups = defaultdict(list)
    for s, day, v in data["observations"]:
        values = groups[s]
        normal = normals.get((s, int(day[5:7])))
        if normal is not None and v is not None:
            values.append(v - normal)
    return {
        s: [len(v), str(Fraction(sum(v), len(v))) if v else None]
        for s, v in groups.items()
    }


print(json.dumps(solve(json.load(sys.stdin)), allow_nan=False))
