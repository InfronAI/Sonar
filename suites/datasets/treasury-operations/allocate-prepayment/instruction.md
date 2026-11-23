# Allocate a prepaid service charge across months

Allocate a nonnegative integer amount in cents over dates in the nonempty half-open service interval [start,end), in UTC civil days. Give every day the integer quotient and give the first remainder days one extra cent. Aggregate by YYYY-MM. Include every service month, even when its allocation is zero.

Create `/app/solve.py`. Read one JSON value from stdin and print one JSON value to stdout. See `/app/example.json` for a worked example.
