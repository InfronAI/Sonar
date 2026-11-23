import json
import sys


def solve(data):
    nodes = data["entries"]
    output = []
    for node in data["requests"]:
        seen = set()
        path = []
        while node is not None and node in nodes and node not in seen:
            seen.add(node)
            label, node = nodes[node]
            path.append(label)
        output.append(path[::-1] if node is None else None)
    return output


print(json.dumps(solve(json.load(sys.stdin)), allow_nan=False))
