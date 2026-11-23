#!/bin/sh
set -eu
reward_dir=${SONAR_EVAL_REWARD_DIR:-/logs/verifier}
mkdir -p "$reward_dir"
printf '0\n' > "$reward_dir/reward.txt"
if python3 - "$(dirname "$0")/cases.json" <<'PY'
import json
import sqlite3
import sys
from pathlib import Path

program = Path.cwd() / "query.sql"

def evaluate(data):
    with sqlite3.connect(":memory:") as db:
        db.executescript("CREATE TABLE readings (id INTEGER PRIMARY KEY, site TEXT NOT NULL, minute INTEGER NOT NULL, value INTEGER);\n")
        for table, rows in data.items():
            for row in rows:
                placeholders = ", ".join("?" for _ in row)
                db.execute(f"INSERT INTO {table} VALUES ({placeholders})", row)
        db.execute("PRAGMA query_only = ON")
        return db.execute(program.read_text(encoding="utf-8")).fetchall()

for index, case in enumerate(json.loads(Path(sys.argv[1]).read_text()), 1):
    actual = evaluate(case["input"])
    if json.dumps(actual, sort_keys=True, allow_nan=False) != json.dumps(case["expected"], sort_keys=True):
        raise SystemExit(f"Case {index} produced an incorrect result")
PY
then
    printf '1\n' > "$reward_dir/reward.txt"
fi
