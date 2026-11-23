import json
import sys


from collections import defaultdict


def solve(data):
    parent = {}

    def root(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in data["links"]:
        a, b = root(a), root(b)
        parent[max(a, b)] = min(a, b)
    visits = defaultdict(set)
    for member, visit in data["visits"]:
        visits[root(member)].add(visit)
    return {m: len(v) for m, v in visits.items()}


print(json.dumps(solve(json.load(sys.stdin)), allow_nan=False))
