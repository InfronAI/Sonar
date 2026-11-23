import math

from .common import EvalError


def harbor_grade(result, suite):
    schema = result.get("schema_version", 1) if isinstance(result, dict) else None
    if type(schema) is not int or schema != 1:
        raise EvalError("Unsupported Harbor trial result")
    exception = result.get("exception_info")
    if exception is not None:
        name = exception.get("exception_type", "unknown") if isinstance(exception, dict) else "unknown"
        status = "timeout" if "Timeout" in str(name) else "error"
        return {"status": status, "reward": None, "reason": f"Harbor exception: {name}"}
    verifier = result.get("verifier_result")
    rewards = verifier.get("rewards") if isinstance(verifier, dict) else None
    value = rewards.get(suite["reward_key"]) if isinstance(rewards, dict) else None
    if type(value) not in (int, float) or not math.isfinite(value):
        raise EvalError(f"Missing finite Harbor reward '{suite['reward_key']}'")
    status = "pass" if value >= suite["pass_threshold"] else "fail"
    return {"status": status, "reward": value, "reason": suite["reward_key"]}
