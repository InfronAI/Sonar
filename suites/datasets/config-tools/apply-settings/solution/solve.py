import json
import sys

def apply(base, patch):
    if not isinstance(patch, dict):
        return patch
    result = dict(base) if isinstance(base, dict) else {}
    for key, value in patch.items():
        if value is None:
            result.pop(key, None)
        else:
            result[key] = apply(result.get(key), value)
    return result

data = json.load(sys.stdin)
print(json.dumps(apply(data["base"], data["patch"])))
