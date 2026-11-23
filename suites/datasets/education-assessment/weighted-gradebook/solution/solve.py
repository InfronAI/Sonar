import json
import sys


from collections import defaultdict
from fractions import Fraction


def solve(data):
    students = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for name, group, earned, possible in data["scores"]:
        scores = students[name]
        if possible:
            scores[group][0] += earned
            scores[group][1] += possible
    out = {}
    for name, scores in students.items():
        total = sum(data["weights"][g] for g in scores)
        points = sum(
            Fraction(n, d) * data["weights"][g] for g, (n, d) in scores.items()
        )
        out[name] = str(100 * points / total) if total else None
    return out


print(json.dumps(solve(json.load(sys.stdin)), allow_nan=False))
