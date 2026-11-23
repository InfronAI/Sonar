import json
import sys


from collections import defaultdict


def solve(rows):
    latest = {}
    departments = defaultdict(list)
    for dept, spec, rev, start, end in rows:
        departments[dept]
        if (dept, spec) not in latest or rev > latest[dept, spec][0]:
            latest[dept, spec] = (rev, start, end)
    for (dept, _), (_, start, end) in latest.items():
        if end is not None and end >= start:
            departments[dept].append(end - start)
    output = {}
    for dept, values in departments.items():
        values.sort()
        n = len(values)
        output[dept] = (
            [n, values[(n + 1) // 2 - 1], values[(9 * n + 9) // 10 - 1]]
            if n
            else [0, None, None]
        )
    return output


print(json.dumps(solve(json.load(sys.stdin)), allow_nan=False))
