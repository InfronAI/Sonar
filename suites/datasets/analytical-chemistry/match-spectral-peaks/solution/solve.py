import json
import sys


def solve(data):
    result = []
    for ident, x in data["observed"]:
        options = [
            (abs(x - y), label, y)
            for label, y in data["references"]
            if abs(x - y) <= data["tolerance"]
        ]
        if options:
            _, label, y = min(options)
            result.append([ident, label, x - y])
        else:
            result.append([ident, None, None])
    return result


print(json.dumps(solve(json.load(sys.stdin)), allow_nan=False))
