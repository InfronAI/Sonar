from collections import defaultdict
from math import isfinite
from urllib.parse import quote

from .common import STATUSES, canonical, read_json

try:
    import tomllib
except ImportError:  # Reports also run on Python 3.10 without the optional Harbor environment.
    tomllib = None


def run_files(state, filename):
    return (p for p in (state / "runs").glob("*/" + filename) if not p.parent.is_symlink())


def summaries(state):
    return sorted((read_json(p) for p in run_files(state, "summary.json")),
                  key=lambda row: (row["started_at"], row["run_id"]))


def series_key(point, *, across_images=False):
    signature = point.get("benchmark_sha256", point["signature"]) if across_images else point["signature"]
    return (point["track"], signature, point["purpose"], point["provider"], point["base_url"],
            point["model_family"], point["agent_family"], canonical(point.get("inference")), point.get("agent_options_sha256", ""),
            tuple((m["model"]["id"], m["agent"]["id"]) for m in point["members"]))


def points(state, *, member_metrics=False):
    history = []
    previous = {}
    for run in summaries(state):
        families = defaultdict(list)
        for pair in run["pairs"]:
            model = pair["model"]
            families[model["family"], pair["agent"]["family"], model.get("provider", ""),
                     model.get("base_url", ""), canonical(pair.get("inference")), pair["agent"].get("kwargs_sha256", "")].append(pair)
        for (mf, af, provider, endpoint, _, options_hash), pairs in sorted(families.items()):
            fields = ("model", "agent", "counts", "reward_sum", "seconds") if member_metrics else ("model", "agent")
            members = [{key: pair[key] for key in fields} for pair in
                       sorted(pairs, key=lambda p: (p["model"]["id"], p["agent"]["id"]))]
            counts = {key: sum(p["counts"][key] for p in pairs) for key in STATUSES}
            total = sum(counts.values())
            graded = counts["pass"] + counts["fail"]
            point = {k: run[k] for k in ("run_id", "started_at", "finished_at", "track",
                                          "signature", "suite", "timeout_seconds", "repetitions")}
            point.update({k: run[k] for k in ("benchmark_sha256", "environment_sha256", "agent_timeout_seconds") if k in run})
            purpose = run.get("purpose", "evaluation")
            point.update({"model_family": mf, "agent_family": af, "provider": provider, "base_url": endpoint,
                          "purpose": purpose, "members": members, "inference": pairs[0].get("inference"),
                          "agent_options_sha256": options_hash,
                          "counts": counts, "total": total, "pass_rate": counts["pass"] / total,
                          "mean_reward": sum(p["reward_sum"] for p in pairs) / graded if graded else None,
                          "mean_seconds": sum(p["seconds"] for p in pairs) / total})
            key = series_key(point)
            prior = previous.get(key)
            point["previous_run"] = prior["run_id"] if prior else None
            point["delta_pp"] = round(100 * (point["pass_rate"] - prior["pass_rate"]), 6) if prior else None
            history.append(point)
            previous[key] = point
    return history


def delta(point):
    return "—" if point["delta_pp"] is None else f"{point['delta_pp']:+.1f} pp"


def member_labels(point):
    labels = []
    for member in point["members"]:
        model, agent = member["model"], member["agent"]
        name = model.get("name", model["id"])
        if model["version"] != name:
            name += "@" + model["version"]
        if point["provider"]:
            name = point["provider"] + "/" + name
        version = agent["version"]
        actual = agent.get("reported_versions")
        if actual and actual != [version]:
            version += " (reported " + ", ".join(actual) + ")"
        labels.append(f"{name} × {agent['id']}@{version}")
    return ", ".join(labels)


def print_history(history):
    if not history:
        print("No completed runs.")
        return
    print("RUN (UTC)\tPURPOSE / TRACK / SUITE\tMODEL FAMILY × AGENT FAMILY\tPASS/TOTAL\tERROR/TIMEOUT\tΔ pp\tVERSIONS\tINFERENCE")
    for p in history:
        c = p["counts"]
        settings = "unrecorded" if p.get("inference") is None else canonical(
            {k: v for k, v in p["inference"].items() if v is not None})
        print(f"{p['run_id']}\t{p['purpose']} / {p['track']} / {p['suite']['id']}@{p['suite']['version']}:{p['signature'][:8]}"
              f"\t{p['model_family']} × {p['agent_family']}\t{c['pass']}/{p['total']} ({p['pass_rate']:.1%})"
              f"\t{c['error']}/{c['timeout']}\t{delta(p)}\t{member_labels(p)}\t{settings}")


def frozen_agent_limits(plan, run_root):
    if plan.get("agent_timeout_seconds") is not None:
        return [plan["agent_timeout_seconds"]]
    if tomllib is None:
        return []
    limits = set()
    task_root = run_root / "tasks"
    for case in plan.get("suite", {}).get("cases", []):
        manifest = (task_root / case["id"] / "task.toml").resolve()
        if not manifest.is_relative_to(task_root):
            return []
        try:
            with manifest.open("rb") as source:
                config = tomllib.load(source)
        except (OSError, ValueError):
            return []
        default = config.get("agent", {}).get("timeout_sec")
        for step in config.get("steps") or [{}]:
            value = step.get("agent", {}).get("timeout_sec", default)
            if type(value) not in (int, float) or not isfinite(value) or value <= 0:
                return []
            limits.add(value)
    return sorted(limits)


def trial_logs(run_root, trial_root, row, link):
    """Only offer files that belong to this attempt, including logs from an interrupted Harbor job."""
    logs = {}
    evidence = (run_root / (row.get("evidence") or "")).resolve()
    has_evidence = evidence.is_relative_to(trial_root) and evidence.is_dir()
    source = row.get("harbor_result")
    raw = (run_root / source).resolve() if isinstance(source, str) else None
    folder = raw.parent if raw and raw.is_relative_to(trial_root) and raw.is_file() else None
    if has_evidence:
        argv = evidence / "argv.json"
        if link(trial_root, argv):
            try:
                args = read_json(argv)
                if isinstance(args, list) and "--api-format" in args:
                    logs["api_format"] = args[args.index("--api-format") + 1]
            except (OSError, ValueError, IndexError):
                pass
        if folder is None:
            job = evidence / "jobs/eval"
            agents = [d for pattern in ("*/agent", "trials/*/agent") for d in job.glob(pattern)
                      if d.is_dir() and d.resolve().is_relative_to(trial_root)]
            if len(agents) == 1:
                folder = agents[0].parent
        logs["launcher_log"] = link(trial_root, evidence / "stderr.log")
    if folder:
        agent_dir = folder / "agent"
        logs["trajectory"] = link(trial_root, agent_dir / "trajectory.json")
        logs["trial_log"] = link(trial_root, folder / "trial.log")
        logs["assessment"] = link(trial_root, folder / "verifier/judge.json")
        logs["verifier_log"] = link(trial_root, folder / "verifier/test-stdout.txt")
        logs["submission"] = link(trial_root, folder / "artifacts/submission.md")
        logs["transcripts"] = [(p.name, url) for p in sorted(agent_dir.glob("*.txt")) if (url := link(trial_root, p))]
    return logs


def report_evidence(state, history):
    """Expose trial metrics and links to files inside the run, without embedding raw logs."""
    wanted = {point["run_id"] for point in history}
    evidence = {}
    state_root = state.resolve()

    def link(directory, path):
        path = path.resolve()
        if path.is_relative_to(directory) and path.is_relative_to(state_root) and path.is_file():
            return quote(path.relative_to(state_root).as_posix(), safe="/")
        return None

    for directory in (state / "runs").iterdir() if (state / "runs").is_dir() else ():
        if directory.name not in wanted or not directory.is_dir():
            continue
        run_root = directory.resolve()
        if not run_root.is_relative_to(state_root / "runs"):
            continue
        plan_link = link(run_root, directory / "plan.json")
        plan = read_json(directory / "plan.json") if plan_link else {}
        tasks = {c["id"]: c.get("task_sha256") for c in plan.get("suite", {}).get("cases", [])}
        frozen = {}
        task_root = run_root / "tasks"
        for case in tasks:
            task = (task_root / case).resolve()
            if task.is_relative_to(task_root):
                frozen[case] = [(label, url) for source, label in (
                    ("instruction.md", "Frozen instruction"), ("tests/test.sh", "Frozen verifier"),
                    ("tests/rubric.json", "Frozen rubric"), ("task.toml", "Frozen task manifest"))
                    if (url := link(task, task / source))]
        records = []
        for path in sorted(directory.glob("trials/*/result.json")):
            trial_root = path.parent.resolve()
            if not trial_root.is_relative_to(run_root):
                continue
            result_link = link(trial_root, path)
            if not result_link:
                continue
            row = read_json(path)
            record = {k: row.get(k) for k in ("model", "agent", "case", "attempt", "status",
                                             "reward", "elapsed_seconds", "reason")}
            metadata = row.get("metadata")
            if isinstance(metadata, dict):
                record.update({k: metadata.get(k) for k in ("cli_version", "docker_image_id")})
            record["result"] = result_link
            record["definition"] = frozen.get(record["case"], [])
            source = row.get("harbor_result")
            if isinstance(source, str):
                record["harbor"] = link(trial_root, directory / source)
            record.update(trial_logs(run_root, trial_root, row, link))
            records.append(record)
        bundle = {"plan": plan_link, "trials": records, "tasks": tasks,
                  "agent_limits": frozen_agent_limits(plan, run_root)}
        comparison = directory / "retest.json"
        if url := link(run_root, comparison):
            bundle["retest"] = read_json(comparison)
            bundle["retest_url"] = url
        evidence[directory.name] = bundle
    return evidence
