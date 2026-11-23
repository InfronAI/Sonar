import json
import sys


from collections import Counter


def solve(lines):
    journals = Counter()
    for journal, _, debit, credit in lines:
        journals[journal] += debit - credit
    accounts = Counter()
    for journal, account, debit, credit in lines:
        if journals[journal] == 0:
            accounts[account] += debit - credit
    return {
        "imbalances": {j: v for j, v in journals.items() if v},
        "balances": dict(accounts),
    }


print(json.dumps(solve(json.load(sys.stdin)), allow_nan=False))
