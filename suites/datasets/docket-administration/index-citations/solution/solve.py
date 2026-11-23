import json
import sys


from collections import defaultdict
import re


def solve(paragraphs):
    index = defaultdict(list)
    for paragraph, text in paragraphs:
        for doc, sec in re.findall(r"\[Doc:([A-Z0-9]+)#Sec:([1-9][0-9]*)\]", text):
            key = doc + "#" + sec
            if paragraph not in index[key]:
                index[key].append(paragraph)
    return dict(index)


print(json.dumps(solve(json.load(sys.stdin)), allow_nan=False))
