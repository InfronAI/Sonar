# Calculate laboratory reporting turnaround

Each synthetic laboratory record is [department,specimen,revision,collected_minute,reported_minute_or_null]. Per (department,specimen) keep the highest numeric revision. Omit entries with no report time or with reported time before collection. Per named department return [valid_count,p50,p90] of turnaround minutes using the nearest-rank rule at rank ceil(p*n), starting at 1. Use null percentiles for empty departments.

Create `/app/solve.py`. Read one JSON value from stdin and print one JSON value to stdout. See `/app/example.json` for a worked example.
