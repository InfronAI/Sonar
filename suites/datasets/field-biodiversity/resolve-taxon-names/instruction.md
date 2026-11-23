# Reconcile taxonomic names in a survey

Resolve each recorded plant name through the supplied `aliases` map until a name without an alias is reached. Sum nonnegative specimen counts from [name,count] observations at the terminal name. If a chain enters a cycle, add its count to `unresolved` instead. Return {"accepted":{name:count},"unresolved":integer}. Names are case-sensitive; the supplied authority list fully defines the exercise.

Create `/app/solve.py`. Read one JSON value from stdin and print one JSON value to stdout. See `/app/example.json` for a worked example.
