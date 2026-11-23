import argparse
import getpass
import json
import os
import signal
import sys
from pathlib import Path

from . import images, native, tuning
from .common import DEFAULT_CONFIG, DEFAULT_STATE, EvalError, read_json
from .history import points, print_history, run_files
from .providers import harbor_executable, save_infron_key
from .reporting import write_report
from .runner import create_run, evaluate, inspect_run, prepare_plan, run_path


def as_json(value):
    print(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False))


def parser():
    cli = argparse.ArgumentParser(prog="sonar", description="Evaluate coding agents and models on reproducible Harbor tasks")
    commands = cli.add_subparsers(dest="action", required=True)
    key = commands.add_parser("set-key", help="Save an API key in this workspace")
    key.add_argument("provider", choices=["infron"])
    build = commands.add_parser("build-images", help="Prebuild the agent base and Harbor task images")
    build.add_argument("--suite", type=Path, default=images.ALL_TASKS,
                       help="Harbor task, dataset directory or selection manifest (default: all bundled tasks)")
    build.add_argument("--archive", type=Path, help="also save the resulting images to a Docker tar archive")
    for name, description in [
        ("doctor", "Validate the matrix and local executable paths"),
        ("run", "Execute one complete evaluation matrix"),
        ("resume", "Finish an interrupted run from its frozen plan"),
        ("runs", "List complete and unfinished runs"),
        ("show", "Inspect one run and its trial evidence"),
        ("history", "Read comparable model-family × agent-family time series"),
        ("report", "Rebuild the standalone HTML report"),
    ]:
        cmd = commands.add_parser(name, help=description, description=description)
        if name != "doctor":
            cmd.add_argument("--state", type=Path, default=os.environ.get("SONAR_EVAL_STATE", DEFAULT_STATE),
                             help="persistent result directory (default: project .sonar/)")
        if name in {"doctor", "run"}:
            source = cmd.add_mutually_exclusive_group()
            source.add_argument("--config", type=Path, help="matrix JSON file (default: configs/ollama.json)")
            source.add_argument("--cli", choices=native.PRESETS, help="start this agent CLI once per trial")
            cmd.add_argument("--model", help="exact model ID to pass to the CLI")
            cmd.add_argument("--provider", help="provider ID configured in the selected CLI")
            cmd.add_argument("--model-family", help="stable family for comparisons across model versions")
            cmd.add_argument("--suite", type=Path, help="Harbor task directory, dataset directory or manifest (default: all bundled tasks)")
            cmd.add_argument("--base-url", help="custom provider HTTP API endpoint")
            cmd.add_argument("--api-key-env", help="environment variable holding the custom provider key")
            cmd.add_argument("--agent-version", help="pin the CLI release used for every task")
            cmd.add_argument("--agent-timeout", type=float, dest="agent_timeout_seconds", metavar="SECONDS",
                             help="override Harbor's agent execution time per task or step")
            cmd.add_argument("--trial-timeout", type=float, dest="timeout_seconds", metavar="SECONDS",
                             help="set the wall-clock limit for the whole trial, including setup and verification")
            cmd.add_argument("--thinking", "--reasoning-effort", dest="reasoning_effort", help="model reasoning effort")
            cmd.add_argument("--max-tokens", type=int, help="maximum output tokens per model response")
            cmd.add_argument("--temperature", type=float, help="sampling temperature")
            cmd.add_argument("--top-p", type=float, help="nucleus sampling probability")
            cmd.add_argument("--max-turns", type=int, help="maximum model turns in one trial")
            cmd.add_argument("--max-thinking-tokens", type=int, help="explicit Claude thinking-token budget")
        if name in {"show", "resume"}:
            cmd.add_argument("run_id")
        if name in {"show", "history", "runs"}:
            cmd.add_argument("--json", action="store_true", help="machine-readable output")
    return cli


def matrix_source(args):
    if args.cli:
        suite = args.suite.resolve() if args.suite else images.ALL_TASKS
        return native.matrix(args.cli, args.model, args.provider, args.model_family, suite,
                             args.base_url, args.api_key_env, args.agent_version)
    if any((args.model, args.provider, args.model_family, args.base_url, args.api_key_env, args.agent_version)):
        raise EvalError("Individual model, provider and version options require --cli")
    return args.config or DEFAULT_CONFIG


def doctor(config, suite_path=None, overrides=None):
    plan, _ = prepare_plan(config, suite_path, overrides)
    for model, agent in plan["pairs"]:
        values = {k: v for k, v in plan["inference"][model][agent].items() if v is not None}
        if values:
            print(f"{model} × {agent} · inference {json.dumps(values, sort_keys=True)}")
    for case in plan["suite"]["cases"]:
        image = case["docker_images"]["main"]
        print(f"{case['id']} · {image['image']} · {image['id']}")
    print(f"Harbor {plan['harbor_version']} · {harbor_executable()}")
    platform = plan["docker_platform"]
    print(f"Docker {platform['daemon']} · default platform {platform['default']}")
    trials = len(plan["pairs"]) * len(plan["suite"]["cases"]) * plan["repetitions"]
    print(f"{plan['track']} · {plan['suite']['id']}@{plan['suite']['version']} · "
          f"{len(plan['pairs'])} pairs · {trials} trials · Python {plan['python']}")
    print(f"Evaluation fingerprint {plan['signature']}")
    agent_limit = f"{plan['agent_timeout_seconds']:g} s" if "agent_timeout_seconds" in plan else "from each task"
    print(f"Agent execution limit {agent_limit} · Whole trial limit {plan['timeout_seconds']:g} s")
    print("Matrix and local entry points ready.")
    return 0


def finish(directory, state):
    summary = evaluate(directory)
    history = write_report(state)
    print_history([p for p in history if p["run_id"] == summary["run_id"]])
    print(f"Report {state / 'report.html'}", flush=True)
    return int(any(p["counts"]["error"] or p["counts"]["timeout"] for p in summary["pairs"]))


def list_runs(state):
    rows = []
    for path in sorted(run_files(state, "plan.json"), reverse=True):
        plan = read_json(path)
        scheduled = len(plan["pairs"]) * len(plan["suite"]["cases"]) * plan["repetitions"]
        complete = (path.parent / "summary.json").exists()
        done = scheduled if complete else sum(1 for _ in (path.parent / "trials").glob("*/result.json"))
        rows.append({"run_id": plan["run_id"], "track": plan["track"], "complete": complete,
                     "finished_trials": done, "planned_trials": scheduled})
    return rows


def main(argv=None):
    args = parser().parse_args(argv)
    # Route termination through subprocess cleanup and leave committed trial records resumable.
    signal.signal(signal.SIGTERM, signal.default_int_handler)
    try:
        if args.action == "build-images":
            images.build_images(args.suite, args.archive)
            return 0
        if args.action == "set-key":
            value = getpass.getpass("Infron API key: ") if sys.stdin.isatty() else sys.stdin.readline()
            print(f"Saved credential to {save_infron_key(value)}")
            return 0
        if args.action in {"doctor", "run"}:
            fields = (*tuning.FIELDS, "agent_timeout_seconds", "timeout_seconds")
            overrides = {k: getattr(args, k) for k in fields if getattr(args, k) is not None}
        if args.action == "doctor":
            return doctor(matrix_source(args), args.suite, overrides)
        state = args.state.resolve()
        if args.action == "run":
            return finish(create_run(state, matrix_source(args), args.suite, overrides), state)
        if args.action == "resume":
            return finish(run_path(state, args.run_id), state)
        if args.action == "history":
            data = points(state)
            if args.json:
                as_json(data)
            else:
                print_history(data)
        elif args.action == "report":
            write_report(state)
            print(state / "report.html")
        elif args.action == "runs":
            rows = list_runs(state)
            if args.json:
                as_json(rows)
            else:
                for row in rows:
                    status = "complete" if row["complete"] else "unfinished"
                    print(f"{row['run_id']}  {row['track']}  {status}  "
                          f"{row['finished_trials']}/{row['planned_trials']}")
        elif args.action == "show":
            record = inspect_run(run_path(state, args.run_id))
            if args.json:
                as_json(record)
            else:
                print("MODEL\tAGENT\tCASE\tATTEMPT\tSTATUS\tREASON\tEVIDENCE")
                for tr in record["trials"]:
                    print("\t".join(str(tr[k]) for k in
                                    ("model", "agent", "case", "attempt", "status", "reason", "evidence")))
        return 0
    except KeyboardInterrupt:
        print("Stopped. Use 'sonar runs' to find unfinished runs.", file=sys.stderr)
        return 130
    except (OSError, ValueError, EOFError) as exc:
        print(f"sonar: {exc}", file=sys.stderr)
        return 2
