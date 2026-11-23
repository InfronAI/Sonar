import json
import re
import sys
from collections import Counter

rows, seen, fenced = [], Counter(), False
for line in json.load(sys.stdin)["lines"]:
    if line.startswith("```"):
        fenced = not fenced
        continue
    match = re.fullmatch(r"(#{1,3}) (.+)", line)
    if fenced or not match or not match[2].strip():
        continue
    title = match[2].strip()
    base = re.sub("[^a-z0-9]+", "-", title.lower()).strip("-") or "section"
    seen[base] += 1
    slug = base if seen[base] == 1 else f"{base}-{seen[base]}"
    rows.append([len(match[1]), title, slug])
print(json.dumps(rows))
