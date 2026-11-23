import json
import sys

data = json.load(sys.stdin)
total, weights = data["total_cents"], data["weights"]
denominator = sum(weights.values())
shares, remainders = {}, {}
for name, weight in weights.items():
    shares[name], remainders[name] = divmod(total * weight, denominator)
priority = sorted(weights, key=lambda name: (-remainders[name], name))
for name in priority[:total - sum(shares.values())]:
    shares[name] += 1
print(json.dumps(shares))
