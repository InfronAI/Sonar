import json
import sys


from collections import defaultdict


def solve(visits):
    sites, occupied = set(), defaultdict(set)
    for site, _, complete, species in visits:
        if complete:
            sites.add(site)
            for name in species:
                occupied[name].add(site)
    return {name: [len(seen), len(sites)] for name, seen in occupied.items()}


print(json.dumps(solve(json.load(sys.stdin)), allow_nan=False))
