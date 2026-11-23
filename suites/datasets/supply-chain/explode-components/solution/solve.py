import json
import sys


from collections import Counter


def solve(data):
    needed = Counter()
    stack = list(data["orders"])
    while stack:
        part, units = stack.pop()
        children = data["bom"].get(part, [])
        if children:
            stack.extend((child, q * units) for child, q in children)
        else:
            needed[part] += units
    return {
        p: q - data["on_hand"].get(p, 0)
        for p, q in needed.items()
        if q > data["on_hand"].get(p, 0)
    }


print(json.dumps(solve(json.load(sys.stdin)), allow_nan=False))
