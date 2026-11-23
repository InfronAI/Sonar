"""Public experiment definitions for reports, independent of credentials and the runtime."""
import shlex
from functools import lru_cache

from .common import ROOT, read_json
from .config import load_suite, matrix_definition, task_hash
from .native import agent_presets, matrix

# Illustrative single-pair runs use the same two-task suite so readers can change one variable.
CLI_EXAMPLES = (
    ("Run a local model", "pi", "ollama", "qwen3-vl:2b-instruct", "Qwen3-VL"),
    ("Use a native provider", "codex", "openai", "gpt-6.2-astra", "Astra"),
    ("Route a model through Infron", "claude-code", "infron", "baidu/ernie-5.5-flash-preview", "ERNIE"),
    ("Route a model through Infron", "claude-code", "infron", "anthropic/claude-opus-5.5", "Opus"),
)


def experiments(root=ROOT):
    root = root.resolve()
    presets = agent_presets(root)
    hash_task = lru_cache(maxsize=None)(task_hash)
    domains = {suite: domain for domain, names in read_json(root / "suites/domains.json").items() for suite in names}
    suites = {}
    for path in sorted((root / "suites/datasets").iterdir()):
        if not path.is_dir() or not ((path / "task.toml").is_file() or any(path.glob("*/task.toml"))):
            continue
        suite, origins = load_suite(path, hash_task)
        for case in suite["cases"]:
            task = origins[case["id"]]
            instruction = (task / "instruction.md").read_text(encoding="utf-8")
            heading = next((line[2:].strip() for line in instruction.splitlines() if line.startswith("# ")), case["id"])
            case.update(title=heading, instruction=instruction, path=task.relative_to(root).as_posix())
            verifier = task / "tests/test.sh"
            if verifier.is_file():
                case["verifier_script"] = verifier.read_text(encoding="utf-8")
            fixtures = task / "tests/cases.json"
            if fixtures.is_file():
                data = read_json(fixtures)
                if isinstance(data, list):
                    case["fixture_count"] = len(data)
            if case.get("judge"):
                case["rubric"] = read_json(task / "tests/rubric.json")
        suites[suite["id"]] = {"path": path.relative_to(root).as_posix(), "cases": suite["cases"],
                               "domain": domains.get(suite["id"], "Other")}
    def entry(name, source, args, **origin):
        check = shlex.join(["./sonar", "doctor", *args])
        item = {"name": name, "check": check, **origin}
        try:
            plan, _ = matrix_definition(source, environ={}, presets=presets, hash_task=hash_task)
        except (OSError, ValueError, KeyError, TypeError):
            return {**item, "command": check, "unavailable": True, "pairs": []}
        return {**item, "command": shlex.join(["./sonar", "run", *args]), "suite": plan["suite"]["id"],
                "tasks": len(plan["suite"]["cases"]), "repetitions": plan["repetitions"],
                "pairs": [(plan["agents"][a], plan["models"][m]) for m, a in plan["pairs"]]}

    matrices = [entry(path.name, path, ["--config", path.relative_to(root).as_posix()], path=path.relative_to(root).as_posix())
                for path in sorted((root / "configs").glob("*.json"))]
    suite = "suites/datasets/sql-analytics"
    for scenario, name, provider, model, family in CLI_EXAMPLES:
        source = matrix(name, model, provider, family, root / suite)
        matrices.append(entry(f"{presets[name]['family']} × {family}", source,
                              ["--cli", name, "--provider", provider, "--model", model, "--model-family", family,
                               "--suite", suite], scenario=scenario))
    return suites, matrices
