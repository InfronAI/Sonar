# Aggregate events into UTC hours

Input contains `events` as `[ISO-8601 timestamp, integer delta]` pairs. Every timestamp has a UTC offset or `Z`. Convert to UTC before grouping. Return one `[hour, sum]` per occupied hour in ascending time order, including zero sums. Format each hour as `YYYY-MM-DDTHH:00Z`.

Create `/app/solve.py`. It will be run with Python 3 and one JSON value on stdin. Print one JSON value to stdout. A worked example is available in `/app/example.json`. The verifier also uses other inputs.
