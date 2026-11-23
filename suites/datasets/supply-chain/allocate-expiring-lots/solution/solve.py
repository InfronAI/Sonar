import json
import sys


def solve(data):
    lots = sorted(([exp, i, start, n] for i, start, exp, n in data["lots"]))
    output = []
    for day, rid, quantity in sorted((d, i, q) for i, d, q in data["requests"]):
        taken = []
        for lot in lots:
            exp, ident, start, stock = lot
            if start <= day < exp and stock and quantity:
                amount = min(stock, quantity)
                lot[3] -= amount
                quantity -= amount
                taken.append([ident, amount])
        output.append([rid, taken, quantity])
    return output


print(json.dumps(solve(json.load(sys.stdin)), allow_nan=False))
