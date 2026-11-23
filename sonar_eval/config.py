import hashlib
import math
import os
import re
import shutil
import sys
from copy import deepcopy
from pathlib import Path

from . import tuning
from .common import ROOT, EvalError, fingerprint, read_json
from .native import agent_presets
from .providers import (
    JUDGE_MODEL,
    configure,
    credential,
    harbor_version,
    judge_credential,
)

# Imported tasks may contain private state created before the project was renamed.
IGNORED = {".git", ".sonar", ".harbor-eval", ".harbo", "__pycache__", ".DS_Store"}
ID = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,95}\Z")


def require(condition, message):
    if not condition:
        raise EvalError(message)


def safe_id(value, where):
    require(isinstance(value, str) and ID.fullmatch(value), f"Invalid identifier in {where}: {value!r}")
    return value


def nonempty(obj, key):
    value = obj.get(key)
    require(isinstance(value, str) and value.strip(), f"Expected a nonempty string in {key}")
    return value


def positive_int(value):
    return type(value) is int and value > 0


def numbered(items, where):
    require(isinstance(items, list) and items, f"{where} must be a nonempty list")
    indexed = {}
    for item in items:
        require(isinstance(item, dict), f"Invalid record in {where}")
        key = safe_id(item.get("id"), where)
        require(key not in indexed, f"Duplicate {where} id: {key}")
        indexed[key] = item
    return indexed


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def execution_hash():
    files = ("common.py", "config.py", "execution.py", "runner.py", "native.py", "providers.py", "images.py", "tuning.py")
    return fingerprint({name: file_hash(ROOT / "sonar_eval" / name) for name in files})


def task_hash(root):
    entries = []
    for folder, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in IGNORED)
        for name in sorted(set(dirs + files) - IGNORED):
            path = Path(folder) / name
            key = path.relative_to(root).as_posix()
            if path.is_symlink():
                target = os.readlink(path)
                require(not os.path.isabs(target) and path.resolve().is_relative_to(root),
                        f"Harbor task link points outside its snapshot: {key}")
                entries.append([key, "link", target])
            elif path.is_file():
                entries.append([key, "file", path.stat().st_mode & 0o111, file_hash(path)])
            elif path.is_dir():
                entries.append([key, "dir"])
            else:
                raise EvalError(f"Unsupported task file: {path}")
    return fingerprint(entries)


def load_suite(path, hash_task=task_hash):
    base = path.parent
    if path.is_dir():
        base = path
        roots = [path] if (path / "task.toml").is_file() else sorted(
            child for child in path.iterdir() if child.is_dir() and (child / "task.toml").is_file())
        require(roots, f"No Harbor task.toml files in {path}")
        suite = {"id": path.name, "version": "1", "grader": "harbor", "reward_key": "reward",
                 "pass_threshold": 1, "cases": [{"id": root.name, "path": str(root.relative_to(path))}
                                                for root in roots]}
    else:
        suite = read_json(path)
    require(isinstance(suite, dict), "Suite must be an object")
    safe_id(suite.get("id"), "suite")
    nonempty(suite, "version")
    require(suite.get("grader") == "harbor", "Expected a Harbor task directory, dataset or task manifest")
    origins = {}
    for case_id, case in numbered(suite.get("cases"), "cases").items():
        root = (base / nonempty(case, "path")).resolve()
        for required in ["task.toml", "instruction.md"]:
            require((root / required).is_file(), f"Missing Harbor task file: {root / required}")
        origins[case_id] = root
        case.pop("path")
        case["task_sha256"] = hash_task(root)
        rubric_path = root / "tests/rubric.json"
        if rubric_path.is_file():
            rubric = read_json(rubric_path)
            if isinstance(rubric, dict) and rubric.get("schema") == "sonar-rubric-v1":
                require(rubric.get("model") == JUDGE_MODEL and rubric.get("provider") == "infron",
                        f"Unsupported rubric judge in {case_id}")
                case["judge"] = {"provider": "infron", "model": JUDGE_MODEL}
                case.setdefault("pass_threshold", rubric.get("pass_threshold"))
        if "pass_threshold" in case:
            value = case["pass_threshold"]
            require(type(value) in (int, float) and math.isfinite(value), f"Invalid pass threshold for {case_id}")
    nonempty(suite, "reward_key")
    threshold = suite.get("pass_threshold", 1)
    require(type(threshold) in (int, float) and math.isfinite(threshold), "pass_threshold must be finite")
    suite["pass_threshold"] = threshold
    return suite, origins


def matrix_components(cfg, presets):
    require(cfg.get("purpose", "evaluation") == "evaluation", "Only model-driven evaluations are supported")
    models = numbered(cfg.get("models"), "models")
    entries = cfg.get("agents")
    require(isinstance(entries, list) and entries, "agents must be a nonempty list")
    for item in entries:
        if isinstance(item, str):
            require(item in presets, f"Unknown agent preset: {item}")
            require(presets[item]["version"], f"Missing package version for {item} in docker/agents/package.json")
    agents = numbered([presets[item] if isinstance(item, str) else item for item in entries], "agents")
    for component in [*models.values(), *agents.values()]:
        nonempty(component, "family")
    for model in models.values():
        nonempty(model, "name")
        nonempty(model, "version")
        if any(key in model for key in ("provider", "base_url", "api_key_env")):
            nonempty(model, "provider")
    for agent in agents.values():
        require(agent.get("driver") == "harbor", "Expected a Harbor Agent driver")
        name = nonempty(agent, "name")
        require(name not in {"oracle", "nop"}, "Select a model-driven Harbor Agent")
        nonempty(agent, "version")
        options = agent.get("kwargs", {})
        require(isinstance(options, dict) and all(isinstance(v, str) for v in options.values()),
                "Harbor kwargs must map names to strings")
    pairs = cfg.get("pairs", [[m, a] for m in models for a in agents])
    require(isinstance(pairs, list) and pairs, "Expected at least one pair")
    for pair in pairs:
        require(isinstance(pair, list) and len(pair) == 2 and all(isinstance(i, str) for i in pair)
                and pair[0] in models and pair[1] in agents, f"Unknown model/agent pair: {pair!r}")
    require(len({tuple(p) for p in pairs}) == len(pairs), "Duplicate model/agent pair")
    return models, agents, pairs


def matrix_definition(source, suite_path=None, overrides=None, *, environ=None, presets=None, hash_task=task_hash):
    """Validate public experiment settings without starting Harbor or reading credentials."""
    if isinstance(source, dict):
        cfg, base = deepcopy(source), ROOT
    else:
        path = source.resolve()
        cfg, base = read_json(path), path.parent
    require(isinstance(cfg, dict) and type(cfg.get("schema")) is int and cfg["schema"] == 1,
            "Expected matrix schema 1")
    track = nonempty(cfg, "track")
    repeats = cfg.get("repetitions", 1)
    overrides = dict(overrides or {})
    timeout = overrides.pop("timeout_seconds", cfg.get("timeout_seconds", 60))
    agent_timeout = overrides.pop("agent_timeout_seconds", cfg.get("agent_timeout_seconds"))
    require(positive_int(repeats), "repetitions must be a positive integer")
    require(type(timeout) in (int, float) and math.isfinite(timeout) and timeout > 0,
            "timeout_seconds must be positive and finite")
    if agent_timeout is not None:
        require(type(agent_timeout) in (int, float) and math.isfinite(agent_timeout) and agent_timeout > 0,
                "agent_timeout_seconds must be positive and finite")
    models, agents, pairs = matrix_components(cfg, agent_presets() if presets is None else presets)
    for model in models.values():
        if "provider" in model:
            configure(model, environ=environ)
    inference = {}
    for m, a in pairs:
        inference.setdefault(m, {})[a] = tuning.resolve(cfg.get("inference", {}), models[m], agents[a],
                                                        overrides or {}, environ=environ)
    suite, origins = load_suite((suite_path or base / nonempty(cfg, "suite")).resolve(), hash_task)
    plan = {"schema": 1, "track": track, "purpose": "evaluation", "suite": suite, "models": models,
            "agents": agents, "pairs": pairs, "inference": inference, "repetitions": repeats,
            "timeout_seconds": float(timeout)}
    if agent_timeout is not None:
        plan["agent_timeout_seconds"] = float(agent_timeout)
    return plan, origins


def load_plan(source, suite_path=None, overrides=None):
    plan, origins = matrix_definition(source, suite_path, overrides)
    for model_id in dict.fromkeys(m for m, _ in plan["pairs"]):
        credential(plan["models"][model_id])
    if any(case.get("judge") for case in plan["suite"]["cases"]):
        judge_credential()
    plan.update(protocol=1, grader_sha256=file_hash(ROOT / "sonar_eval/grading.py"),
                harbor_version=harbor_version(), execution_sha256=execution_hash(), python=sys.version.split()[0])
    plan["runner_sha256"] = fingerprint({p.name: file_hash(p) for p in sorted((ROOT / "sonar_eval").glob("*.py"))})
    comparison_fields = ("protocol", "suite", "grader_sha256", "timeout_seconds", "agent_timeout_seconds",
                         "repetitions", "harbor_version")
    plan["benchmark_sha256"] = fingerprint({k: plan[k] for k in comparison_fields if k in plan})
    return plan, origins


def snapshot_tasks(origins, directory):
    for case_id, source in origins.items():
        target = directory / case_id
        require(not target.resolve().is_relative_to(source),
                "State directory must be outside the Harbor task being copied")
        shutil.copytree(source, target, symlinks=True, ignore=shutil.ignore_patterns(*IGNORED))
