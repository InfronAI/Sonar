import os
import signal
import subprocess
import time

from . import native, tuning
from .common import EvalError, read_json, write_json
from .grading import harbor_grade
from .providers import harbor_env, harbor_executable, harbor_model, judge_credential


def execute(argv, work, evidence, timeout, env=None, cancel=None):
    with (evidence / "stdout.log").open("wb") as out, (evidence / "stderr.log").open("wb") as err:
        proc = subprocess.Popen(argv, cwd=work, stdin=subprocess.DEVNULL, stdout=out, stderr=err, env=env,
                                start_new_session=os.name == "posix")
        try:
            if cancel is not None:
                deadline = time.monotonic() + timeout
                while proc.poll() is None:
                    if cancel.is_set():
                        raise KeyboardInterrupt
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise subprocess.TimeoutExpired(argv, timeout)
                    cancel.wait(min(.2, remaining))
                return proc.returncode
            return proc.wait(timeout=timeout)
        except BaseException:
            # Harbor handles SIGTERM by cancelling its trial and removing the Compose project.
            try:
                proc.terminate()
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                pass
            finally:
                if os.name == "posix":
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                elif proc.poll() is None:
                    proc.kill()
                proc.wait()
            raise


def harbor_trial(plan, model, agent, case, run_dir, work, evidence, cancel=None):
    jobs = evidence / "jobs"
    argv = [harbor_executable(), "run", "-p", str(run_dir / "tasks" / case["id"]), "-a", agent["name"],
            "-o", str(jobs), "--job-name", "eval", "-k", "1", "-n", "1", "-r", "0"]
    options, env = harbor_model(agent["name"], model)
    argv.extend(options)
    if "handbook_sha256" in plan:
        argv.extend(["--extra-instruction-path", str(run_dir / "handbook.md")])
    settings = plan.get("inference", {}).get(model["id"], {}).get(agent["id"], {})
    env = tuning.launch_env(agent["name"], env, settings)
    for variable, field in tuning.ENV_FIELDS.get(agent["name"], {}).items():
        if settings.get(field) is not None:
            argv.extend(["--ae", f"{variable}={settings[field]}"])
    kwargs = tuning.harbor_options(agent["name"], agent.get("kwargs", {}), settings, model)
    if agent["name"] in native.PRESETS:
        kwargs["version"] = agent["version"]
        kwargs["skip_install"] = "true"
    for key, value in kwargs.items():
        argv.extend(["--ak", f"{key}={value}"])
    if case.get("judge"):
        # Preflight validates the fixed verifier and its single host credential reference.
        argv.append("--yes")
    write_json(evidence / "argv.json", argv)
    child_env = harbor_env(env)
    if case.get("judge"):
        child_env["SONAR_JUDGE_KEY"] = judge_credential()
    code = execute(argv, work, evidence, plan["timeout_seconds"], env=child_env, cancel=cancel)
    job = jobs / "eval"
    files = sorted(set(job.glob("*/result.json")) | set(job.glob("trials/*/result.json")))
    if len(files) != 1:
        raise EvalError(f"Harbor exited {code} with {len(files)} trial results. See the job logs")
    source = str(files[0].relative_to(run_dir))
    try:
        raw = read_json(files[0])
    except (OSError, ValueError) as exc:
        return {"status": "error", "reward": None, "reason": str(exc), "harbor_result": source}
    rules = {**plan["suite"], "pass_threshold": case.get("pass_threshold", plan["suite"]["pass_threshold"])}
    try:
        observation = harbor_grade(raw, rules)
    except EvalError as exc:
        observation = {"status": "error", "reward": None, "reason": str(exc)}
    if not isinstance(raw, dict):
        return {**observation, "harbor_result": source}
    info = raw.get("agent_info") or {}
    if not isinstance(info, dict):
        return {"status": "error", "reward": None, "reason": "Invalid agent_info in the Harbor trial result",
                "harbor_result": source}
    metadata = {"requested_model": model["name"], "configured_provider": model.get("provider"),
                "harbor_agent": info.get("name"), "cli_version": info.get("version"),
                "harbor_model_info": info.get("model_info"), "verifier": raw.get("verifier_result")}
    if "docker_images" in case:
        metadata["docker_image_id"] = case["docker_images"]["main"]["id"]
    if case.get("judge"):
        metadata.update(judge=case["judge"], pass_threshold=rules["pass_threshold"])
        assessment = files[0].parent / "verifier/judge.json"
        if assessment.is_file() and read_json(assessment).get("status") == "judge_error":
            observation.update(status="error", reward=None, reason="Rubric judge error (see assessment)")
    if code and observation["status"] in {"pass", "fail"}:
        observation.update(status="error", reward=None, reason=f"Harbor exited with status {code}. See the job logs")
    return {**observation, "metadata": metadata, "harbor_result": source}


def run_trial(plan, model, agent, case, attempt, run_dir, evidence, *, cancel=None):
    work = evidence / "work"
    work.mkdir()
    started = time.monotonic()
    try:
        result = harbor_trial(plan, model, agent, case, run_dir, work, evidence, cancel)
    except subprocess.TimeoutExpired:
        result = {"status": "timeout", "reward": None, "reason": "Trial deadline exceeded"}
    except (OSError, ValueError, UnicodeError, RecursionError) as exc:
        result = {"status": "error", "reward": None, "reason": str(exc)}
    return {**result, "model": model["id"], "agent": agent["id"], "case": case["id"],
            "inference": plan.get("inference", {}).get(model["id"], {}).get(agent["id"]),
            "attempt": attempt, "elapsed_seconds": round(time.monotonic() - started, 6),
            "evidence": evidence.relative_to(run_dir).as_posix()}
