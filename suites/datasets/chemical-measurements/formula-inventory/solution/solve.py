import json
import sys


from collections import Counter
import re


def solve(formulas):
    output = []
    for formula in formulas:
        total = Counter()
        for fragment in formula.split("."):
            tokens = re.findall(r"[A-Z][a-z]*|[0-9]+|[()]", fragment)
            factor = int(tokens.pop(0)) if tokens[0].isdigit() else 1
            stack = [Counter()]
            i = 0
            while i < len(tokens):
                token = tokens[i]
                i += 1
                if token == "(":
                    stack.append(Counter())
                    continue
                atoms = stack.pop() if token == ")" else {token: 1}
                multiple = 1
                if i < len(tokens) and tokens[i].isdigit():
                    multiple = int(tokens[i])
                    i += 1
                stack[-1].update({el: n * multiple for el, n in atoms.items()})
            total.update({el: n * factor for el, n in stack[0].items()})
        output.append(dict(total))
    return output


print(json.dumps(solve(json.load(sys.stdin)), allow_nan=False))
