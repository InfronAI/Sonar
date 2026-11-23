# Compute an empirical quantile from frequencies

Observations [value,integer_frequency] may be unordered and values can repeat. Frequencies are nonnegative. For each query [numerator,denominator] between zero and one inclusive, use rank max(1,ceil(numerator/denominator * total_frequency)) and the ascending expanded order. Return the value at that rank, or null if total weight is zero. Frequencies can be extremely large; work on frequencies directly.

Create `/app/solve.py`. Read one JSON value from stdin and print one JSON value to stdout. See `/app/example.json` for a worked example.
