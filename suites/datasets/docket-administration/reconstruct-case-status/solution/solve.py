import json
import sys


def solve(data):
    states = {}
    for case, day, seq, action in sorted(data["events"]):
        if day > data["cutoff"]:
            continue
        if action == "file":
            states.setdefault(case, "open")
        elif case in states:
            states[case] = {"reopen": "open", "stay": "stayed", "close": "closed"}[
                action
            ]
    return states


print(json.dumps(solve(json.load(sys.stdin)), allow_nan=False))
