# Standardize bird counts by completed survey effort

Rows are [site,minutes,birds,valid]. Pool only valid rows with positive minutes per site, summing birds and minutes first. Compute birds per hour as a reduced fraction string, using integers without '/1'. Return null for a named site with no eligible effort. A zero bird count on a valid visit still adds its minutes.

Create `/app/solve.py`. Read one JSON value from stdin and print one JSON value to stdout. See `/app/example.json` for a worked example.
