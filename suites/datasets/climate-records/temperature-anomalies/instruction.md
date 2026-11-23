# Calculate station anomalies from monthly normals

Normals are [station,month_1_to_12,normal_tenths_C]. Observations are [station,ISO_date,temperature_tenths_C_or_null] with at most one per station/day. For each station with observations, subtract its corresponding calendar month normal and average the signed differences over days with both values available. Return [eligible_day_count,exact_mean_as_reduced_fraction_string] or [0,null].

Create `/app/solve.py`. Read one JSON value from stdin and print one JSON value to stdout. See `/app/example.json` for a worked example.
