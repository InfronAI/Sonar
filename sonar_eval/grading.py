import math

from .common import EvalError


def harbor_grade(result, suite):
    schema = result.get("schema_version", 1) if isinstance(result, dict) else None
    if type(schema) is not int or schema != 1:
        raise EvalError("Unsupported Harbor trial result")
    phases = [("trial", result)]
    steps = result.get("step_results")
    if steps is not None:
        if not isinstance(steps, list) or any(not isinstance(s, dict) for s in steps):
            raise EvalError("Invalid Harbor step results")
        phases.extend((f"step {step.get('step_name', i)}", step) for i, step in enumerate(steps, 1))
    for phase, record in phases:
        exception = record.get("exception_info")
        if exception is not None:
            name = exception.get("exception_type", "unknown") if isinstance(exception, dict) else "unknown"
            status = "timeout" if "Timeout" in str(name) else "error"
            return {"status": status, "reward": None, "reason": f"Harbor {phase} exception: {name}"}
    if result.get("reward_valid", True) is not True:
        return {"status": "error", "reward": None, "reason": "Harbor did not confirm a valid reward"}
    verifier = result.get("verifier_result")
    rewards = verifier.get("rewards") if isinstance(verifier, dict) else None
    value = rewards.get(suite["reward_key"]) if isinstance(rewards, dict) else None
    if type(value) not in (int, float) or not math.isfinite(value):
        raise EvalError(f"Missing finite Harbor reward '{suite['reward_key']}'")
    status = "pass" if value >= suite["pass_threshold"] else "fail"
    return {"status": status, "reward": value, "reason": suite["reward_key"]}
