import json
import sys


from collections import Counter
from datetime import date, timedelta


def solve(data):
    start, end = map(date.fromisoformat, (data["start"], data["end"]))
    days = (end - start).days
    share, extra = divmod(data["cents"], days)
    months = Counter()
    for i in range(days):
        months[(start + timedelta(days=i)).isoformat()[:7]] += share + (i < extra)
    return dict(months)


print(json.dumps(solve(json.load(sys.stdin)), allow_nan=False))
