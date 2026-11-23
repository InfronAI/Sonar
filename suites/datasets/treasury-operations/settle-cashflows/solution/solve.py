import json
import sys


def solve(data):
    closing = dict(data["opening"])
    latest = {}
    for ident, rev, *fields in data["entries"]:
        if ident not in latest or rev > latest[ident][0]:
            latest[ident] = (rev, *fields)
    for _, date, ccy, delta, status in latest.values():
        if status == "posted" and date <= data["cutoff"]:
            closing[ccy] = closing.get(ccy, 0) + delta
    return closing


print(json.dumps(solve(json.load(sys.stdin)), allow_nan=False))
