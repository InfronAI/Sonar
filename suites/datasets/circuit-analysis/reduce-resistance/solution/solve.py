import json
import sys


from fractions import Fraction


def equivalent(network):
    if isinstance(network, int):
        return Fraction(network)
    mode, children = next(iter(network.items()))
    values = [equivalent(child) for child in children]
    if mode == "series":
        return sum(values)
    return Fraction(0) if 0 in values else 1 / sum(1 / r for r in values)


def solve(data):
    return [str(equivalent(network)) for network in data]


print(json.dumps(solve(json.load(sys.stdin)), allow_nan=False))
