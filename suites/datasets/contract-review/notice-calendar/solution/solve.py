import json
import sys


from datetime import date, timedelta


def solve(data):
    closed = set(data["holidays"])

    def is_open(day):
        return day.weekday() < 5 and day.isoformat() not in closed

    due = {}
    for ident, start, days in data["notices"]:
        current = date.fromisoformat(start)
        while days or not is_open(current):
            current += timedelta(days=1)
            if days and is_open(current):
                days -= 1
        due[ident] = current.isoformat()
    return due


print(json.dumps(solve(json.load(sys.stdin)), allow_nan=False))
