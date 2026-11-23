import json
import sys

data = json.load(sys.stdin)
start, end = data["window"]
merged = []
for left, right in sorted(data["intervals"]):
    left, right = max(left, start), min(right, end)
    if left >= right:
        continue
    if merged and left <= merged[-1][1]:
        merged[-1][1] = max(merged[-1][1], right)
    else:
        merged.append([left, right])
print(json.dumps({"intervals": merged, "duration": sum(b - a for a, b in merged)}))
