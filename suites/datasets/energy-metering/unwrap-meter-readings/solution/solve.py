import json
import sys


from collections import defaultdict


def solve(data):
    readings = defaultdict(dict)
    for meter, time, value in data["rows"]:
        readings[meter][time] = value
    result = {}
    for meter, samples in readings.items():
        samples = [v for _, v in sorted(samples.items())]
        intervals = list(zip(samples, samples[1:]))
        result[meter] = [
            sum((b - a) % data["modulus"] for a, b in intervals),
            sum(b < a for a, b in intervals),
        ]
    return result


print(json.dumps(solve(json.load(sys.stdin)), allow_nan=False))
