import json
import sys


from collections import Counter
from datetime import date


def solve(data):
    cutoff = date.fromisoformat(data["as_of"])
    paid = Counter()
    for invoice, day, cents in data["payments"]:
        if date.fromisoformat(day) <= cutoff:
            paid[invoice] += cents
    buckets = dict.fromkeys(("current", "1-30", "31-60", "61+"), 0)
    for invoice, issue, due, cents in data["invoices"]:
        if date.fromisoformat(issue) > cutoff:
            continue
        age = (cutoff - date.fromisoformat(due)).days
        bucket = (
            "current"
            if age <= 0
            else "1-30"
            if age <= 30
            else "31-60"
            if age <= 60
            else "61+"
        )
        buckets[bucket] += max(0, cents - paid[invoice])
    return buckets


print(json.dumps(solve(json.load(sys.stdin)), allow_nan=False))
