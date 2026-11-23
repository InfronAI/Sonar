import json
import sys


from collections import Counter


def solve(data):
    accepted, unresolved = Counter(), 0
    for name, count in data["observations"]:
        visited = set()
        while name in data["aliases"] and name not in visited:
            visited.add(name)
            name = data["aliases"][name]
        if name in visited:
            unresolved += count
        else:
            accepted[name] += count
    return {"accepted": dict(accepted), "unresolved": unresolved}


print(json.dumps(solve(json.load(sys.stdin)), allow_nan=False))
