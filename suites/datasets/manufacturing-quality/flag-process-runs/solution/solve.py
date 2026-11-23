import json
import sys


from collections import defaultdict


def solve(data):
    groups = defaultdict(dict)
    for line, t, x in data["readings"]:
        groups[line][t] = x
    output = []
    for line, values in sorted(groups.items()):
        groups_of_minutes = []
        for t, x in sorted(values.items()):
            side = (
                None
                if x is None or x == data["center"]
                else ("high" if x > data["center"] else "low")
            )
            if side is None:
                continue
            if (
                groups_of_minutes
                and groups_of_minutes[-1][0] == side
                and groups_of_minutes[-1][2] + 1 == t
            ):
                groups_of_minutes[-1][2] = t
            else:
                groups_of_minutes.append([side, t, t])
        output.extend(
            [line, side, a, b]
            for side, a, b in groups_of_minutes
            if b - a + 1 >= data["k"]
        )
    return output


print(json.dumps(solve(json.load(sys.stdin)), allow_nan=False))
