import json
import sys


def solve(data):
    free = [0] * data["rooms"]
    out = []
    for earliest, ident, duration in sorted(
        (max(s, a), i, d) for i, s, a, d in data["visits"]
    ):
        start, room = min((max(earliest, t), r) for r, t in enumerate(free))
        free[room] = start + duration
        out.append([ident, room + 1, start, free[room]])
    return out


print(json.dumps(solve(json.load(sys.stdin)), allow_nan=False))
