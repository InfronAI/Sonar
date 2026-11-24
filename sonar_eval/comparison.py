"""Compare two frozen runs without changing their scores or experiment history."""
from .common import EvalError, fingerprint
from .measurements import aligned_outcomes
from .runner import inspect_run


def select_pair(plan, choice):
    if choice is None:
        if len(plan["pairs"]) != 1:
            raise EvalError("Select the model and agent IDs for each multi-pair run")
        return plan["pairs"][0]
    if list(choice) not in plan["pairs"]:
        raise EvalError(f"Unknown pair {choice} in {plan['run_id']}")
    return choice


def selection(directory, choice):
    run = inspect_run(directory)
    plan = run["plan"]
    model, agent = select_pair(plan, choice)
    conditions = {field: plan.get(field) for field in (
        "track", "purpose", "benchmark_sha256", "environment_sha256", "execution_sha256",
        "harbor_version", "grader_sha256", "agent_timeout_seconds", "timeout_seconds",
        "repetitions", "handbook_sha256")}
    conditions.update(workers=plan.get("workers", 1), endpoint_workers=plan.get("endpoint_workers", 1),
                      judge_workers=plan.get("judge_workers", 1), suite=[plan["suite"]["id"], plan["suite"]["version"]],
                      docker_platform=plan.get("docker_platform"),
                      model={k: plan["models"][model].get(k) for k in ("name", "family", "version", "provider", "base_url")},
                      agent={k: plan["agents"][agent].get(k) for k in ("name", "family", "version", "driver")},
                      agent_options_sha256=fingerprint(plan["agents"][agent].get("kwargs", {})),
                      inference=plan.get("inference", {}).get(model, {}).get(agent))
    trials = [t for t in run["trials"] if (t["model"], t["agent"]) == (model, agent)]
    hashes = {c["id"]: c.get("task_sha256") for c in plan["suite"]["cases"]}
    return ({"run": plan["run_id"], "model": model, "agent": agent, "conditions": conditions,
             "committed": len(trials), "planned": len(hashes) * plan["repetitions"],
             "complete": run["summary"] is not None}, trials, hashes)


def compare_runs(before, after, before_pair=None, after_pair=None):
    a, old, old_hashes = selection(before, before_pair)
    b, new, new_hashes = selection(after, after_pair)
    conditions = [k for k, v in a["conditions"].items() if v != b["conditions"][k]]
    rows, transitions = aligned_outcomes(old, new, old_hashes, new_hashes)
    return {"baseline": a, "candidate": b, "changed_conditions": conditions,
            "transitions": transitions, "tasks": rows}
