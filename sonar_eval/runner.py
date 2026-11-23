import shutil
import sys
import tempfile
import uuid
from collections import Counter
from pathlib import Path

from . import images
from .common import (
    ROOT,
    STATUSES,
    EvalError,
    fingerprint,
    lock,
    read_json,
    utc_now,
    write_json,
)
from .config import (
    execution_hash,
    file_hash,
    load_plan,
    safe_id,
    snapshot_tasks,
    task_hash,
)
from .execution import run_trial
from .providers import harbor_version


class SnapshotChanged(EvalError):
    pass


def trials(plan):
    index = 0
    for model_id, agent_id in plan["pairs"]:
        for case in plan["suite"]["cases"]:
            for attempt in range(1, plan["repetitions"] + 1):
                index += 1
                yield index, plan["models"][model_id], plan["agents"][agent_id], case, attempt


def trial_dir(directory, index):
    return directory / "trials" / f"{index:06d}"


def run_path(state, run_id):
    path = state / "runs" / safe_id(run_id, "run id")
    if not (path / "plan.json").is_file():
        raise EvalError(f"Unknown run: {run_id}")
    return path


def prepare_plan(config_path, suite_path=None, overrides=None):
    plan, origins = load_plan(config_path, suite_path, overrides)
    resolved = images.resolve_images(plan, origins)
    identities = {}
    for case in plan["suite"]["cases"]:
        case_id = case["id"]
        records = resolved.get(case_id, {})
        if "main" not in records:
            raise EvalError(f"Missing prebuilt main image for {case_id}")
        case["docker_images"] = records
        identities[case_id] = {role: record["id"] for role, record in records.items()}
    # A multi-platform OCI index can have the same ID on both ARM and x86.
    plan["docker_platform"] = images.docker_platform()
    plan["environment_sha256"] = fingerprint([plan["docker_platform"], identities])
    plan["signature"] = fingerprint([plan["benchmark_sha256"], plan["environment_sha256"]])
    return plan, origins


def create_run(state, config_path, suite_path=None, overrides=None):
    plan, origins = prepare_plan(config_path, suite_path, overrides)
    started = utc_now()
    run_id = started.replace(":", "").replace("-", "").replace(".", "") + "-" + uuid.uuid4().hex[:8]
    directory = state / "runs" / run_id
    directory.mkdir(parents=True, exist_ok=False)
    try:
        snapshot_tasks(origins, directory / "tasks")
        for case in plan["suite"]["cases"]:
            task = directory / "tasks" / case["id"]
            if task_hash(task) != case["task_sha256"]:
                raise SnapshotChanged(f"Task changed during snapshot: {case['id']}")
            images.pin_snapshot(task, case["docker_images"], plan.get("agent_timeout_seconds"))
            case["snapshot_sha256"] = task_hash(task)
        plan.update({"run_id": run_id, "started_at": started})
        write_json(directory / "plan.json", plan)
    except BaseException:
        shutil.rmtree(directory)
        raise
    return directory


def validate_snapshot(plan, directory):
    if "execution_sha256" in plan and plan["execution_sha256"] != execution_hash():
        raise SnapshotChanged("Execution code changed since the run began. Start a new run with the current code")
    if file_hash(ROOT / "sonar_eval" / "grading.py") != plan["grader_sha256"]:
        raise SnapshotChanged("Grader changed since the run began. Start a new run with the current grader")
    if plan["suite"]["grader"] == "harbor":
        if "harbor_version" in plan and harbor_version() != plan["harbor_version"]:
            raise SnapshotChanged("Harbor version changed since this run began")
        if "docker_platform" in plan and images.docker_platform() != plan["docker_platform"]:
            raise SnapshotChanged("Docker platform differs from the frozen plan")
        for case in plan["suite"]["cases"]:
            path = directory / "tasks" / case["id"]
            if not path.is_dir() or task_hash(path) != case.get("snapshot_sha256", case["task_sha256"]):
                raise SnapshotChanged(f"Harbor task snapshot differs: {case['id']}")
            for record in case.get("docker_images", {}).values():
                images.ensure_pinned(record["id"])


def component_info(item):
    return {k: item[k] for k in ("id", "family", "version", "name", "provider", "base_url", "driver") if k in item}


def combine_pair(model, agent, results):
    counts = Counter(r["status"] for r in results)
    agent_summary = component_info(agent)
    if agent.get("kwargs"):
        agent_summary["kwargs_sha256"] = fingerprint(agent["kwargs"])
    observed = sorted({r["metadata"]["cli_version"] for r in results
                       if isinstance(r.get("metadata"), dict) and r["metadata"].get("cli_version")})
    if observed:
        agent_summary["reported_versions"] = observed
    return {"model": component_info(model), "agent": agent_summary, "inference": results[0].get("inference"),
            "counts": {key: counts[key] for key in STATUSES},
            "reward_sum": sum(r["reward"] for r in results if r["reward"] is not None),
            "seconds": sum(r["elapsed_seconds"] for r in results)}


def evaluate(directory):
    with lock(directory / ".worker.lock"):
        final_path = directory / "summary.json"
        if final_path.exists():
            return read_json(final_path)
        plan = read_json(directory / "plan.json")
        validate_snapshot(plan, directory)
        print(f"Running {plan['run_id']}  ({plan['track']})", file=sys.stderr, flush=True)
        by_pair = {(m, a): [] for m, a in plan["pairs"]}
        for index, model, agent, case, attempt in trials(plan):
            trial = trial_dir(directory, index)
            result_path = trial / "result.json"
            if result_path.is_file():
                result = read_json(result_path)
            else:
                trial.mkdir(parents=True, exist_ok=True)
                evidence = Path(tempfile.mkdtemp(prefix="execution-", dir=trial))
                result = run_trial(plan, model, agent, case, attempt, directory, evidence)
                write_json(result_path, result)
            by_pair[model["id"], agent["id"]].append(result)
        pairs = [combine_pair(plan["models"][m], plan["agents"][a], results)
                 for (m, a), results in by_pair.items()]
        summary = {"schema": 1, "run_id": plan["run_id"], "started_at": plan["started_at"],
                   "finished_at": utc_now(), "track": plan["track"], "signature": plan["signature"],
                   "purpose": plan.get("purpose", "evaluation"),
                   "suite": {k: plan["suite"][k] for k in ("id", "version", "grader")},
                   "repetitions": plan["repetitions"], "timeout_seconds": plan["timeout_seconds"],
                   "pairs": pairs}
        for key in ("benchmark_sha256", "environment_sha256", "agent_timeout_seconds"):
            if key in plan:
                summary[key] = plan[key]
        write_json(final_path, summary)
        return summary


def inspect_run(directory):
    plan = read_json(directory / "plan.json")
    results = []
    for index, *_ in trials(plan):
        path = trial_dir(directory, index) / "result.json"
        if path.is_file():
            results.append(read_json(path))
    summary = directory / "summary.json"
    return {"plan": plan, "trials": results, "summary": read_json(summary) if summary.is_file() else None}
