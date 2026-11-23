# Consolidate effective contract amendments

Build the clause register for the supplied fictional contract at ISO date `as_of`. Start with `original`, a clause-ID to text map. Each amendment is [effective_date, sequence, clause_id, text_or_null]. Apply all amendments through that date in ascending date and numeric sequence order, independent of file order. Null repeals a clause; a later amendment may reinstate it. Return the active clause map. Date/sequence pairs are unique.

Create `/app/solve.py`. Read one JSON value from stdin and print one JSON value to stdout. See `/app/example.json` for a worked example.
