import json
import sys


from collections import Counter


def solve(data):
    net = Counter()
    for src, dst, current in data["edges"]:
        net[src] -= current
        net[dst] += current
    return [
        [k, net[k]]
        for k in sorted(net, key=lambda k: (-abs(net[k]), k))
        if abs(net[k]) > data["tolerance"]
    ]


print(json.dumps(solve(json.load(sys.stdin)), allow_nan=False))
