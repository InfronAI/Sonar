import json
import sys
from collections import Counter

changes = Counter()
for start, end in json.load(sys.stdin)["bookings"]:
    if start < end:
        changes[start] += 1
        changes[end] -= 1
active, peak, earliest = 0, 0, None
for stamp in sorted(changes):
    active += changes[stamp]
    if active > peak:
        peak, earliest = active, stamp
print(json.dumps([peak, earliest]))
