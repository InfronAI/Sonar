# Measure peak concurrent bookings

Input `bookings` is a list of half-open integer intervals `[start,end]` with `start <= end`. Ignore zero-duration intervals. Return `[maximum simultaneous bookings, earliest time that maximum holds]`. Return `[0,null]` if no nonempty booking exists. A booking ending exactly when another begins contributes no overlap.

Create `/app/solve.py`. It will be run with Python 3 and one JSON value on stdin. Print one JSON value to stdout. A worked example is available in `/app/example.json`. The verifier also uses other inputs.
