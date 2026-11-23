#!/bin/sh
set -eu
reward_dir=${SONAR_EVAL_REWARD_DIR:-/logs/verifier}
mkdir -p "$reward_dir"
printf '0\n' > "$reward_dir/reward.txt"
if python3 - "$(dirname "$0")/cases.json" <<'PY'
import json
import subprocess
import sys
from pathlib import Path


def evaluate(data):
    check = """
import copy
import json
import sys
from event_page import solve

data = json.load(sys.stdin)
original = copy.deepcopy(data)
result = solve(data)
if data != original:
    raise ValueError("The pagination function mutated its input")
print(json.dumps(result))
"""
    result = subprocess.run([sys.executable, "-c", check], text=True, input=json.dumps(data),
                            capture_output=True, timeout=4, check=True)
    return json.loads(result.stdout)

for index, case in enumerate(json.loads(Path(sys.argv[1]).read_text()), 1):
    actual = evaluate(case["input"])
    if json.dumps(actual, sort_keys=True, allow_nan=False) != json.dumps(case["expected"], sort_keys=True):
        raise SystemExit(f"Case {index} produced an incorrect result")
PY
then
    printf '1\n' > "$reward_dir/reward.txt"
fi
