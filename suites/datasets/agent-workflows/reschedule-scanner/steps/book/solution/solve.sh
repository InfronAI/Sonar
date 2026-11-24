#!/bin/sh
set -eu
python3 - <<'PY'
import sqlite3
with sqlite3.connect("calendar.db") as db:
    db.execute("INSERT INTO bookings VALUES ('pamphlet', 'B', 2)")
PY
