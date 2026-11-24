"""Exercise an installed CLI and verifier in isolated, unranked validation state."""
import os
import secrets
import tempfile
from contextlib import nullcontext
from pathlib import Path

from .common import write_json
from .config import matrix_definition
from .runner import create_run, evaluate
from .scripted_endpoint import scripted_server

TASK_MANIFEST = """schema_version = "1.4"
[environment]
docker_image = "sonar-eval/agents:1"
[agent]
timeout_sec = 90.0
[verifier]
environment_mode = "shared"
timeout_sec = 30.0
[[steps]]
name = "check"
"""


def diagnostic_tasks(root, token):
    for case in ("direct", "tool"):
        task = root / case
        step = task / "steps/check"
        tests = task / "tests"
        step.mkdir(parents=True)
        tests.mkdir()
        if case == "direct":
            prompt = f"SONAR_DIRECT_TASK. Write exactly {token} to /tmp/sonar-submission using a shell tool."
        else:
            prompt = ("SONAR_TOOL_TASK. Read /tmp/sonar-code using a shell tool. After receiving its output, "
                      "write precisely that value to /tmp/sonar-submission with a separate shell call.")
            setup = step / "workdir/setup.sh"
            setup.parent.mkdir()
            setup.write_text(f"#!/bin/sh\nprintf '%s\\n' '{token}' > /tmp/sonar-code\n")
        (task / "instruction.md").write_text(prompt + "\n")
        (step / "instruction.md").write_text(prompt + "\n")
        (task / "task.toml").write_text(TASK_MANIFEST)
        verifier = tests / "test.sh"
        verifier.write_text("#!/bin/sh\nset -eu\nmkdir -p /logs/verifier\nscore=0\n"
                            f'''if [ "$(cat /tmp/sonar-submission 2>/dev/null)" = '{token}' ]; then score=1; fi\n'''
                            '''printf '%s\\n' "$score" > /logs/verifier/reward.txt\n''')
        verifier.chmod(0o755)


def check_pair(pair, receipts):
    name, model = pair["agent"]["name"], pair["model"]["name"]
    requested = {k: v for k, v in (pair.get("inference") or {}).items() if v is not None}
    check = {"agent": name, "model": model, "counts": pair["counts"], "requested_inference": requested,
             "passed": pair["counts"]["pass"] == 2}
    if receipts is None:
        return check
    prefix = f'/{name}/{pair["model"]["id"]}/'
    requests = [r for r in receipts if r["path"].startswith(prefix) and r["model"] == model and r["case"]]
    # Some clients also ask for a session title with their own sampling settings and no tools.
    task_requests = [r for r in requests if r["action"] in {"read", "write", "finish"}]
    check["other_requests"] = len(requests) - len(task_requests)
    actions = {case: [r["action"] for r in task_requests if r["case"] == case] for case in ("direct", "tool")}
    check["actions"] = actions
    tool = actions["tool"]
    round_trip = "read" in tool and "write" in tool[tool.index("read") + 1:]
    check["passed"] = check["passed"] and "write" in actions["direct"] and round_trip
    fields = {"max_tokens": ("max_tokens", "max_completion_tokens", "max_output_tokens"),
              "temperature": ("temperature",), "top_p": ("top_p",)}
    observed = {}
    for key, aliases in fields.items():
        if key in requested:
            values = [next((r["fields"][a] for a in aliases if a in r["fields"]), None) for r in task_requests]
            observed[key] = values
            if not values or any(v != requested[key] for v in values):
                check["passed"] = False
    check["observed_inference"] = observed
    return check


def smoke(state, source, overrides, *, scripted=False, bind="127.0.0.1"):
    validation = state / "validation"
    validation.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="smoke-", dir=validation))
    token = "SNR-" + secrets.token_hex(8)
    suite = directory / "cli-diagnostic"
    diagnostic_tasks(suite, token)
    options = {"agent_timeout_seconds": 90, "timeout_seconds": 180, **overrides, "workers": 1, "repetitions": 1}
    plan, _ = matrix_definition(source, suite, options)
    advertised = "host.docker.internal" if bind == "127.0.0.1" else bind
    server_context = scripted_server(token, (m["name"] for m in plan["models"].values()), bind) if scripted else nullcontext(None)
    key_var = "SONAR_SCRIPTED_ENDPOINT_KEY"
    original_key = os.environ.get(key_var)
    try:
        with server_context as server:
            if server:
                os.environ[key_var] = "local-fixture"
                models, pairs = [], []
                for index, (model_id, agent_id) in enumerate(plan["pairs"], 1):
                    model = plan["models"][model_id]
                    driver = plan["agents"][agent_id]["name"]
                    key = f"route-{index}"
                    settings = plan["inference"][model_id][agent_id]
                    models.append({**model, "id": key, "provider": "scripted", "api_key_env": key_var,
                                   "base_url": f"http://{advertised}:{server.server_port}/{driver}/{key}/v1",
                                   "inference": {k: v for k, v in settings.items() if v is not None}})
                    pairs.append([key, agent_id])
                source = {"schema": 1, "track": "cli-diagnostic", "agents": list(plan["agents"].values()),
                          "models": models, "pairs": pairs}
                if "handbook" in plan:
                    handbook = directory / "handbook.md"
                    handbook.write_text(plan["handbook"], encoding="utf-8")
                    options["handbook"] = handbook.resolve()
            run = create_run(directory, source, suite, options, purpose="smoke")
            try:
                summary = evaluate(run)
            finally:
                if server:
                    write_json(directory / "requests.json", server.receipts)
            checks = [check_pair(pair, server.receipts if server else None) for pair in summary["pairs"]]
            report = {"run": run.name, "scripted": scripted, "checks": checks}
            write_json(directory / "diagnostic.json", report)
            return directory, report
    finally:
        if scripted:
            if original_key is None:
                os.environ.pop(key_var, None)
            else:
                os.environ[key_var] = original_key
