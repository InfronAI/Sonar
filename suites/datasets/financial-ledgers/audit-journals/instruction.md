# Audit posted journal entries

A ledger export contains lines [journal, account, debit_cents, credit_cents]. Lines for the same journal can be separated. A journal is balanced when its total debits equal its total credits. Return an object with (1) `imbalances` mapping only unbalanced journals to their signed debit-minus-credit difference and (2) `balances` mapping accounts to their signed net across balanced journals only. Include accounts with zero net if a balanced journal used them. Amounts are nonnegative integers.

Create `/app/solve.py`. Read one JSON value from stdin and print one JSON value to stdout. See `/app/example.json` for a worked example.
