import json
import sys
from collections import defaultdict
from datetime import datetime, timezone

totals = defaultdict(int)
for stamp, delta in json.load(sys.stdin)["events"]:
    instant = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    hour = instant.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:00Z")
    totals[hour] += delta
print(json.dumps(sorted(totals.items())))
