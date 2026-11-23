import json
import sys
from collections import defaultdict
from pathlib import Path

root = Path(sys.argv[1])
groups = defaultdict(list)
for path in root.rglob("*"):
    if path.is_file():
        groups[path.read_bytes()].append(path.relative_to(root).as_posix())
matches = [sorted(group) for group in groups.values() if len(group) > 1]
print(json.dumps(sorted(matches)))
