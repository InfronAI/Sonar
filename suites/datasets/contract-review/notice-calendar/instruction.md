# Compute contractual notice dates

Implement only the calendar rules written in this fictional agreement. For each notice [id, served_date, business_days], day one is the first open day strictly after service. Saturdays, Sundays, and listed ISO holiday dates are closed. For a zero-day period use the service date if open or the next open day. Return a map of IDs to due dates in ISO format. The supplied holidays are the complete calendar.

Create `/app/solve.py`. Read one JSON value from stdin and print one JSON value to stdout. See `/app/example.json` for a worked example.
