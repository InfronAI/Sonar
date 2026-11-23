import json
import sys


from collections import defaultdict


def solve(items):
    books = defaultdict(list)
    invalid = []
    for copy, text in items:
        code = text.replace("-", "").replace(" ", "")
        if (
            len(code) == 10
            and code[:9].isascii()
            and code[:9].isdigit()
            and code[-1] in "0123456789X"
        ):
            digits = [int(c) for c in code[:9]] + [
                10 if code[-1] == "X" else int(code[-1])
            ]
            if sum((10 - i) * n for i, n in enumerate(digits)) % 11 == 0:
                stem = "978" + code[:9]
                code = stem + str(
                    -sum((1 if i % 2 == 0 else 3) * int(c) for i, c in enumerate(stem))
                    % 10
                )
        if (
            len(code) == 13
            and code.startswith(("978", "979"))
            and code.isascii()
            and code.isdigit()
            and sum((1 if i % 2 == 0 else 3) * int(c) for i, c in enumerate(code)) % 10
            == 0
        ):
            books[code].append(copy)
        else:
            invalid.append(copy)
    return {
        "books": {k: sorted(v) for k, v in books.items()},
        "invalid": sorted(invalid),
    }


print(json.dumps(solve(json.load(sys.stdin)), allow_nan=False))
