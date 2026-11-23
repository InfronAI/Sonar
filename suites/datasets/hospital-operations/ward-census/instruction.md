# Measure occupied bed time from ward stays

Stays in this synthetic hospital are [ward,bed,start_minute,end_minute_or_null]. For the specified half-open reporting window [lo,hi), clip each stay, using hi for null ends. Union overlapping or touching intervals for each physical (ward,bed) to avoid duplicate billing. Sum distinct occupied bed-minutes by ward. Include every ward named in the stays, even with zero minutes.

Create `/app/solve.py`. Read one JSON value from stdin and print one JSON value to stdout. See `/app/example.json` for a worked example.
