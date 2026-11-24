#!/bin/sh
set -eu
python3 - <<'PY'
import sqlite3
with sqlite3.connect("calendar.db") as db:
    db.execute("UPDATE bookings SET scanner='A', slot=3 WHERE job='pamphlet'")
PY
