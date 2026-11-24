#!/bin/sh
set -eu
dest=${SONAR_EVAL_REWARD_DIR:-/logs/verifier}
mkdir -p "$dest"
python3 - "$dest/reward.txt" <<'PY'
import sqlite3
import sys
from pathlib import Path

def matches(rows, expected):
    with sqlite3.connect(":memory:") as db:
        db.execute("CREATE TABLE readings(sku TEXT, tick INTEGER, sequence INTEGER, units INTEGER)")
        db.executemany("INSERT INTO readings VALUES (?, ?, ?, ?)", rows)
        db.execute("PRAGMA query_only=ON")
        db.set_progress_handler(lambda: 1, 100000)
        return db.execute(Path("query.sql").read_text()).fetchmany(len(expected) + 1) == expected

cases = [
    ([], []),
    ([("z", 8, 3, 5), ("x", 0, 1, 7), ("z", 8, 2, 19), ("x", 2, 0, 0), ("z", 7, 9, 88)],
     [("x", 0), ("z", 5)]),
    ([("p", 3, 8, 1), ("p", 3, 9, 6), ("a", 9, 0, 3)], [("a", 3), ("p", 6)])
]
try:
    passed = all(matches(rows, expected) for rows, expected in cases)
except (OSError, UnicodeError, sqlite3.Error):
    passed = False
Path(sys.argv[1]).write_text(f"{int(passed)}\n")
PY
