# Compute monitored uptime

Input contains a half-open integer observation `window` `[start,end]` and unsorted half-open `intervals`. Clip intervals to the window, discard empty intersections, and merge overlapping or touching intervals. Return `{"intervals":[...],"duration":n}` in time order. Duration is the sum of the merged lengths.

Create `/app/solve.py`. It will be run with Python 3 and one JSON value on stdin. Print one JSON value to stdout. A worked example is available in `/app/example.json`. The verifier also uses other inputs.
