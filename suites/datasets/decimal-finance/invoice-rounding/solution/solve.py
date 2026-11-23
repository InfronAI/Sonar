import json
import sys
from decimal import Decimal, ROUND_HALF_UP

def round_cents(amount):
    return int(amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

data = json.load(sys.stdin)
net = sum(round_cents(Decimal(row["unit_price"]) * row["quantity"] * 100) for row in data["lines"])
tax = round_cents(Decimal(net) * data["tax_bps"] / 10000)
print(json.dumps({"net_cents": net, "tax_cents": tax, "total_cents": net + tax}))
