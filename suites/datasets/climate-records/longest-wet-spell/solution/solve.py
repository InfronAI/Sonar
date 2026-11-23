import json
import sys


from collections import defaultdict
from datetime import date


def solve(data):
    days = defaultdict(dict)
    for station, day, rain in data["rows"]:
        days[station][date.fromisoformat(day)] = rain
    output = {}
    for station, readings in days.items():
        length = best = 0
        start = best_start = previous = None
        for day, rain in sorted(readings.items()):
            if rain is None or rain < data["threshold"]:
                length = 0
            else:
                if not length or (day - previous).days != 1:
                    length, start = 0, day
                length += 1
                if length > best:
                    best, best_start = length, start.isoformat()
            previous = day
        output[station] = [best, best_start]
    return output


print(json.dumps(solve(json.load(sys.stdin)), allow_nan=False))
