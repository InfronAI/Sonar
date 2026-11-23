# Measure first-pass yield by production line

Inspections are [line,unit,minute,sequence,passed]. A unit belongs to one line. Use the earliest (minute,sequence) for each unit regardless of input order. Return per line [units_inspected,units_passing_first_inspection,units_passing_any_inspection]. The sequence breaks time ties; a later failure does not erase an earlier pass.

Create `/app/solve.py`. Read one JSON value from stdin and print one JSON value to stdout. See `/app/example.json` for a worked example.
