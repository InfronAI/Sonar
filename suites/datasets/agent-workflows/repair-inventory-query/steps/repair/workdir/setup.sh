#!/bin/sh
set -eu
python3 - <<'PY' > feedback.txt
import sqlite3
from pathlib import Path

print("Public ledger: ('A', 8, 5, 2), ('A', 8, 7, 0), ('B', 5, 1, 12).")
print("Expected rows: [('A', 0), ('B', 12)]")
with sqlite3.connect(":memory:") as db:
    db.execute("CREATE TABLE readings(sku TEXT, tick INTEGER, sequence INTEGER, units INTEGER)")
    db.executemany("INSERT INTO readings VALUES (?, ?, ?, ?)", [('A', 8, 5, 2), ('A', 8, 7, 0), ('B', 5, 1, 12)])
    db.execute("PRAGMA query_only=ON")
    db.set_progress_handler(lambda: 1, 50000)
    try:
        print("Your rows (up to ten):", db.execute(Path("query.sql").read_text()).fetchmany(10))
    except (OSError, UnicodeError, sqlite3.Error) as err:
        print("Query unavailable:", err)
PY
