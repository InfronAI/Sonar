import json
import sys


def solve(grid):
    land = {
        (i, j) for i, line in enumerate(grid) for j, c in enumerate(line) if c == "#"
    }
    unseen = set(land)
    patches = []
    while unseen:
        stack = [unseen.pop()]
        area = perimeter = 0
        while stack:
            i, j = stack.pop()
            area += 1
            for q in ((i - 1, j), (i + 1, j), (i, j - 1), (i, j + 1)):
                if q not in land:
                    perimeter += 1
                elif q in unseen:
                    unseen.remove(q)
                    stack.append(q)
        patches.append([area, perimeter])
    return sorted(patches, key=lambda p: (-p[0], p[1]))


print(json.dumps(solve(json.load(sys.stdin)), allow_nan=False))
