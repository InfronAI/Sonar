import json
import sys


from bisect import bisect_left
from fractions import Fraction


def solve(data):
    standards = dict(data["standards"])
    responses = sorted(standards)
    result = []
    for x in data["samples"]:
        i = bisect_left(responses, x)
        if x in standards:
            result.append(str(standards[x]))
        elif i == 0 or i == len(responses):
            result.append(None)
        else:
            lo, hi = responses[i - 1 : i + 1]
            result.append(
                str(
                    standards[lo]
                    + Fraction((x - lo) * (standards[hi] - standards[lo]), hi - lo)
                )
            )
    return result


print(json.dumps(solve(json.load(sys.stdin)), allow_nan=False))
