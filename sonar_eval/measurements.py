"""Offline measurements derived from committed Harbor evidence."""
from collections import Counter, defaultdict
from datetime import datetime
from math import isfinite
from statistics import median

USAGE = {"n_input_tokens": "Input tokens", "n_cache_tokens": "Cached input tokens",
         "n_output_tokens": "Output tokens", "cost_usd": "Agent-reported cost (USD)"}
PHASES = {"environment_setup": "Environment setup", "agent_setup": "Agent setup",
          "agent_execution": "Agent execution", "verifier": "Verification"}


def number(value):
    return type(value) in (int, float) and isfinite(value) and value >= 0


def seconds(timing):
    if not isinstance(timing, dict):
        return None
    try:
        start, end = [datetime.fromisoformat(timing[k].replace("Z", "+00:00"))
                      for k in ("started_at", "finished_at")]
        duration = (end - start).total_seconds()
    except (AttributeError, KeyError, TypeError, ValueError):
        return None
    return duration if duration >= 0 else None


def harbor_measurements(raw):
    if not isinstance(raw, dict):
        return {}
    steps = raw.get("step_results") or []
    if not isinstance(steps, list) or any(not isinstance(s, dict) for s in steps):
        return {}
    measured = {}
    for key in USAGE:
        values = [s.get("agent_result") for s in steps or [raw]]
        values = [v.get(key) if isinstance(v, dict) else None for v in values]
        if all(number(v) for v in values):
            measured[key] = sum(values)
    for key in PHASES:
        timings = steps if steps and key in {"agent_execution", "verifier"} else [raw]
        durations = [seconds(s.get(key)) for s in timings]
        if all(d is not None for d in durations):
            measured[key] = sum(durations)
    return measured


def summarize_measurements(trials):
    stats = {}
    for key in (*USAGE, *PHASES):
        values = [t["measurements"][key] for t in trials if key in t.get("measurements", {})]
        if values:
            stats[key] = {"observed": len(values), "median": median(values), "sum": sum(values)}
    return stats


def repeatability(trials, repetitions):
    groups = defaultdict(list)
    for t in trials:
        groups[t["case"]].append(t)
    complete = []
    for attempts in groups.values():
        if (len(attempts) == repetitions and {a["attempt"] for a in attempts} == set(range(1, repetitions + 1))
                and all(a["status"] in {"pass", "fail"} for a in attempts)):
            complete.append(sum(a["status"] == "pass" for a in attempts))
    graded = [t for t in trials if t["status"] in {"pass", "fail"}]
    return {"graded": len(graded), "passed": sum(t["status"] == "pass" for t in graded),
            "tasks": len(groups), "complete": len(complete), "any": sum(n > 0 for n in complete),
            "all": complete.count(repetitions), "mixed": sum(0 < n < repetitions for n in complete)}


def aligned_outcomes(before, after, old_hashes, new_hashes):
    """A task ID aligns only when its frozen revision agrees."""
    left = {(t["case"], t["attempt"]): t for t in before}
    right = {(t["case"], t["attempt"]): t for t in after}
    rows, transitions = [], Counter()
    for key in sorted(left.keys() | right.keys()):
        a, b = left.get(key), right.get(key)
        same = bool(old_hashes.get(key[0])) and old_hashes.get(key[0]) == new_hashes.get(key[0])
        pair = [t["status"] if t else None for t in (a, b)]
        if a and b and same:
            transitions[tuple(pair)] += 1
        rows.append({"case": key[0], "attempt": key[1], "same_revision": same,
                     "before": pair[0], "after": pair[1],
                     "reward_before": a.get("reward") if a else None, "reward_after": b.get("reward") if b else None})
    return rows, [{"before": a, "after": b, "count": n} for (a, b), n in sorted(transitions.items())]
