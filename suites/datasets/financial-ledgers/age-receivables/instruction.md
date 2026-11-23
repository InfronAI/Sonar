# Age outstanding invoice balances

As of the inclusive ISO date `as_of`, consider invoices [id, issue_date, due_date, cents] already issued. Payments [invoice_id, date, cents] reduce only that invoice and only through the cutoff. Exclude balances at or below zero. Return outstanding cents by age past due in buckets `current` (due today or later), `1-30`, `31-60`, `61+`. Include all four buckets even when empty. Dates are civil dates. Invoice IDs are unique.

Create `/app/solve.py`. Read one JSON value from stdin and print one JSON value to stdout. See `/app/example.json` for a worked example.
