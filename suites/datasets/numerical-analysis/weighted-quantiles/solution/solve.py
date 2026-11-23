import json
import sys


from collections import Counter


def solve(data):
    weights = Counter()
    for value, n in data["observations"]:
        weights[value] += n
    total = sum(weights.values())
    samples = sorted(weights.items())
    result = []
    for n, d in data["quantiles"]:
        rank = max(1, (total * n + d - 1) // d)
        cumulative = 0
        answer = None
        for value, w in samples:
            cumulative += w
            if cumulative >= rank:
                answer = value
                break
        result.append(answer)
    return result


print(json.dumps(solve(json.load(sys.stdin)), allow_nan=False))
