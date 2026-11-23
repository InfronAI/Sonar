import json
import sys


def solve(data):
    result = dict(data["original"])
    for day, sequence, clause, text in sorted(data["amendments"]):
        if day > data["as_of"]:
            break
        if text is None:
            result.pop(clause, None)
        else:
            result[clause] = text
    return result


print(json.dumps(solve(json.load(sys.stdin)), allow_nan=False))
