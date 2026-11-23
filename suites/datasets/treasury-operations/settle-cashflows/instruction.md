# Reconcile daily cash positions across currencies

Given opening balances (currency to integer minor units), a cutoff ISO date, and entries [id,revision,settle_date,currency,delta,status], use the greatest revision per entry ID. Revisions per ID are unique. Apply only winning records marked posted and settled on or before cutoff. Return closing balances by currency; include opening currencies and those with qualifying entries, even when balance is zero.

Create `/app/solve.py`. Read one JSON value from stdin and print one JSON value to stdout. See `/app/example.json` for a worked example.
