import json
import sys


def merge(intervals):
    out = []
    for a, b in sorted(intervals):
        if a >= b:
            continue
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def solve(data):
    free = []
    blocks = merge(data["blocked"])
    for a, b in merge(data["windows"]):
        cursor = a
        for x, y in blocks:
            if y <= cursor or x >= b:
                continue
            if cursor < x:
                free.append((cursor, x))
            cursor = max(cursor, y)
        if cursor < b:
            free.append((cursor, b))
    length = data["exposure"]
    return [
        t for a, b in free for t in range(a, b - length + 1, length + data["readout"])
    ]


print(json.dumps(solve(json.load(sys.stdin)), allow_nan=False))
