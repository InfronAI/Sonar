#!/bin/sh
set -eu
dest=${SONAR_EVAL_REWARD_DIR:-/logs/verifier}
mkdir -p "$dest"
python3 - "$dest/reward.txt" <<'PY'
import sqlite3
import sys
from pathlib import Path
expected = [("atlas", "A", 1), ("ledger", "B", 1), ("map", "A", 2), ("pamphlet", "A", 3)]
try:
    with sqlite3.connect("file:calendar.db?mode=ro", uri=True) as db:
        actual = db.execute("SELECT job, scanner, slot FROM bookings ORDER BY job").fetchmany(5)
    passed = actual == expected
except sqlite3.Error:
    passed = False
Path(sys.argv[1]).write_text(f"{int(passed)}\n")
PY
