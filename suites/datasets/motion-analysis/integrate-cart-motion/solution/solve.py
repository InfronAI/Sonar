import json
import sys


def solve(data):
    elapsed, position, velocity = 0, 2 * data["x"], data["v"]
    result = []
    for seconds, acceleration in data["segments"]:
        position += 2 * velocity * seconds + acceleration * seconds * seconds
        velocity += acceleration * seconds
        elapsed += seconds
        result.append([elapsed, position, velocity])
    return result


print(json.dumps(solve(json.load(sys.stdin)), allow_nan=False))
