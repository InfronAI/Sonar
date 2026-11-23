import json
import sys
from collections import defaultdict

totals = defaultdict(int)
for store, sku, quantity in json.load(sys.stdin)["sales"]:
    totals[store, sku] += quantity

pivot = {}
for (store, sku), quantity in totals.items():
    if quantity:
        pivot.setdefault(store, {})[sku] = quantity
print(json.dumps(pivot))
