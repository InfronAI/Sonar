# Bill demand by time-of-use tariff intervals

Usage intervals are [start,end,watts] in integer minutes, half-open, and may overlap (loads add). Tariffs [start,end,rate] are disjoint, half-open periods; rates are integer billing units per watt-minute. For each tariff in supplied order return [watt_minutes,charge] using only its overlap with the usage intervals. Ignore usage outside tariffs. Preserve zero charges and empty periods.

Create `/app/solve.py`. Read one JSON value from stdin and print one JSON value to stdout. See `/app/example.json` for a worked example.
