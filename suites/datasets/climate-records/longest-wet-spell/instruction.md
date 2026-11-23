# Find continuous wet spells at weather stations

Each row [station,ISO_date,rain_tenths_mm_or_null] is a daily observation. Use the last reported value per station/day. A wet day meets or exceeds the supplied threshold. A missing day, null, or dry reading breaks a spell. For each station return [longest_length,earliest_start_date] with [0,null] if none.

Create `/app/solve.py`. Read one JSON value from stdin and print one JSON value to stdout. See `/app/example.json` for a worked example.
