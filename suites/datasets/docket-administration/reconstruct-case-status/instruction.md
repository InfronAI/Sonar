# Reconstruct a docket at a cutoff

Use the rules of this fictional case registry. At cutoff day consider events [case_id,day,sequence,action] in chronological order then sequence order (unique within case/day). A file or reopen sets state to open, stay sets stayed, and close sets closed. Ignore actions before a case is first filed. A duplicate file must not reset an existing case. Return the final state for each filed case, omitting future and never-filed cases.

Create `/app/solve.py`. Read one JSON value from stdin and print one JSON value to stdout. See `/app/example.json` for a worked example.
