import heapq
import json
import sys

data = json.load(sys.stdin)
after = {job: set() for job in data["jobs"]}
degree = dict.fromkeys(after, 0)
for first, second in data["edges"]:
    if second not in after[first]:
        after[first].add(second)
        degree[second] += 1
ready = [job for job, count in degree.items() if count == 0]
heapq.heapify(ready)
order = []
while ready:
    job = heapq.heappop(ready)
    order.append(job)
    for child in after[job]:
        degree[child] -= 1
        if degree[child] == 0:
            heapq.heappush(ready, child)
print(json.dumps(order if len(order) == len(after) else None))
