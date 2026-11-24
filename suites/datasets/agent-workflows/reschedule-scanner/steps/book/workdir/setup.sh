#!/bin/sh
set -eu
python3 - <<'PY'
import sqlite3
with sqlite3.connect("calendar.db") as db:
    db.execute("CREATE TABLE bookings(job TEXT PRIMARY KEY, scanner TEXT NOT NULL, slot INTEGER NOT NULL, UNIQUE(scanner, slot))")
    db.executemany("INSERT INTO bookings VALUES (?, ?, ?)", [("atlas", "A", 1), ("ledger", "B", 1), ("map", "A", 2)])
PY
