import json
import sys


from collections import defaultdict


def solve(data):
    requests = defaultdict(dict)
    for student, course, rank, time in data["requests"]:
        group = requests[course]
        key = (rank, time)
        group[student] = min(key, group.get(student, key))
    result = {}
    for course, capacity in data["capacities"].items():
        order = sorted(
            requests[course], key=lambda student: (requests[course][student], student)
        )
        result[course] = {"admitted": order[:capacity], "waitlist": order[capacity:]}
    return result


print(json.dumps(solve(json.load(sys.stdin)), allow_nan=False))
