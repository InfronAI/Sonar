import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
rows = []
for path in root.rglob("*.txt"):
    relative = path.relative_to(root)
    if path.is_file() and not any(part.startswith(".") for part in relative.parts):
        content = path.read_bytes()
        rows.append([relative.as_posix(), len(content), len(content.decode("utf-8").splitlines())])
print(json.dumps(sorted(rows)))
