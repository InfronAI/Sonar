import json
import sys

data = json.load(sys.stdin)
profiles, name = data["profiles"], data["target"]
seen, layers = set(), []
while name is not None:
    if name in seen:
        result = {"error": "cycle"}
        break
    if name not in profiles:
        result = {"error": "missing"}
        break
    seen.add(name)
    profile = profiles[name]
    layers.append(profile["values"])
    name = profile.get("parent")
else:
    values = {}
    for layer in reversed(layers):
        values.update(layer)
    result = {"values": values}
print(json.dumps(result))
